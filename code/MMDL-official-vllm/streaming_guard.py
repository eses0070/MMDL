"""vLLM 0.11.2 streaming adapter; one persistent event loop per engine."""
import asyncio
from repetition_guard import RepetitionGuard


async def cancel_and_drain(tasks):
    # Construct gather inside the owning running loop, including the empty case.
    for task in tasks:
        task.cancel()
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


async def guarded_generate(engine, prompt, params, request_id, guard):
    stream = engine.generate(prompt, params, request_id)
    finished = False
    last_progress = 0
    try:
        async for output in stream:
            if not output.outputs:
                continue
            answer = output.outputs[0]
            if len(answer.token_ids)-last_progress >= 1024:
                last_progress = len(answer.token_ids)
                print(f"GENERATING {request_id}: {last_progress} tokens", flush=True)
            # A request that already ended is not retroactively aborted.
            if output.finished:
                finished = True
                return output
            evidence = guard.check(answer.text, len(answer.token_ids))
            if evidence:
                await engine.abort(request_id)
                finished = True
                answer.finish_reason = "repetition_abort"
                output.repetition_evidence = evidence
                print(f"REPETITION_ABORT {request_id}: {len(answer.token_ids)} observed tokens", flush=True)
                return output
        raise RuntimeError("Generation stream ended without a terminal result")
    finally:
        try:
            if not finished:
                await engine.abort(request_id)
        finally:
            await stream.aclose()


class StreamingGuardEngine:
    def __init__(self, engine_args):
        from importlib.metadata import version
        if version("vllm") != "0.11.2":
            raise RuntimeError("Streaming guard currently targets vLLM 0.11.2; validate before changing versions")
        self.loop = asyncio.new_event_loop()
        self.counter = 0
        async def create():
            from vllm.engine.arg_utils import AsyncEngineArgs
            from vllm.v1.engine.async_llm import AsyncLLM
            return AsyncLLM.from_engine_args(AsyncEngineArgs(**engine_args))
        try:
            self.engine = self.loop.run_until_complete(create())
        except BaseException:
            self.loop.close()
            raise

    def generate(self, prompts, sampling_params, use_tqdm=False):
        from vllm.sampling_params import RequestOutputKind
        if len(prompts) != 1:
            raise ValueError("Guard adapter supports one request at a time")
        sampling_params.output_kind = RequestOutputKind.CUMULATIVE
        self.counter += 1
        task = self.loop.create_task(guarded_generate(self.engine, prompts[0], sampling_params,
                                                     f"guard-{self.counter}", RepetitionGuard()))
        try:
            return [self.loop.run_until_complete(task)]
        except BaseException:
            self.loop.run_until_complete(cancel_and_drain([task]))
            raise

    def close(self):
        if self.loop.is_closed():
            return
        try:
            async def shutdown():
                try:
                    self.engine.shutdown()
                    await asyncio.sleep(0)
                finally:
                    pending = [task for task in asyncio.all_tasks()
                               if task is not asyncio.current_task()]
                    await cancel_and_drain(pending)
                    await self.loop.shutdown_asyncgens()
                    await self.loop.shutdown_default_executor()
            self.loop.run_until_complete(shutdown())
        finally:
            self.loop.close()

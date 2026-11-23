"""Request-local token suppression using the vLLM 0.11.2 V1 sampler."""
import torch
from vllm.v1.sample.logits_processor import AdapterLogitsProcessor


PARAM = "mmdl_nowait_blocked_ids"


class NoWaitMask(AdapterLogitsProcessor):
    def __init__(self, vllm_config, device, is_pin_memory):
        super().__init__(vllm_config, device, is_pin_memory)
        self.device = device
        self.vocab_size = vllm_config.model_config.get_vocab_size()

    @classmethod
    def validate_params(cls, sampling_params):
        blocked = (sampling_params.extra_args or {}).get(PARAM)
        if blocked is not None and (not isinstance(blocked, list) or not blocked
                                    or any(type(i) is not int or i < 0 for i in blocked)
                                    or blocked != sorted(set(blocked))):
            raise ValueError("NoWait requires sorted, distinct nonnegative token IDs")

    def is_argmax_invariant(self):
        return False

    def new_req_logits_processor(self, params):
        blocked = (params.extra_args or {}).get(PARAM)
        if blocked is None:
            return None
        self.validate_params(params)
        if blocked[-1] >= self.vocab_size:
            raise ValueError("NoWait blocked ID exceeds model vocabulary")
        indices = torch.tensor(blocked, dtype=torch.long, device=self.device)

        def mask(output_ids, logits):
            return logits.index_fill_(0, indices, float("-inf"))

        return mask

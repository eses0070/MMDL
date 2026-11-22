from copy import deepcopy
from fractions import Fraction
import random
import unittest

from numeric_rules import compare_quantities, hybrid_decide, parse_quantity


class Assertions:
    def assertDecision(self, question, reference, candidate, expected):
        result = compare_quantities(question, reference, candidate)
        self.assertEqual(result['status'], 'decided', result)
        self.assertIs(result['decision'], expected, result)

    def assertFallback(self, question, reference, candidate):
        result = compare_quantities(question, reference, candidate)
        self.assertEqual(result['status'], 'fallback', result)
        self.assertIsNone(result['decision'])


class ScalarRules(Assertions, unittest.TestCase):
    def test_decimal_scientific_and_commas(self):
        for left,right in [('1000','1e3'),('12,345.6','12345.600'),('.5','0.50'),('-2.5e-2','-0.025')]:
            with self.subTest(left=left): self.assertDecision('What is the value?',left,right,True)

    def test_exact_fraction_without_float_tolerance(self):
        self.assertDecision('What is the value?','1/8','0.125',True)
        self.assertDecision('What is the value?','1/3','0.333333333333333333',False)
        self.assertDecision('What is the value?',r'\frac{3}{8}','0.375',True)

    def test_large_integer_difference_not_rounded_away(self):
        self.assertDecision('How many?', '9007199254740993','9007199254740992',False)

    def test_negative_sign_preserved(self):
        self.assertDecision('What is the value?','−12','12',False)
        self.assertDecision('What is the value?','-12','−12',True)

    def test_english_number_words(self):
        for left,right in [('eight','8'),('seventy-two','72'),('thirty one','31'),('zero','0'),('9.8 million','9800000')]:
            with self.subTest(left=left): self.assertDecision('How many?',left,right,True)

    def test_full_expression_only(self):
        for answer in ('1+2','2sqrt(2)','x=3','The answer is 3','3 because it follows','3 or 4','not 3','at least 3','about 3','between 3 and 4'):
            with self.subTest(answer=answer): self.assertFallback('What is the value?','3',answer)

    def test_malformed_and_unsafe_expressions_fall_back(self):
        for answer in ('1,25','1.2.3','nan','inf','1/0','1e1000000','__import__("os").system("x")','3; print(4)','', '1'*600):
            with self.subTest(answer=answer): self.assertFallback('What is the value?','3',answer)

    def test_outer_formatting_only(self):
        self.assertDecision('What is the value?','**7**','`7`',True)
        self.assertFallback('What is the value?','7','$7$')

    def test_dates_identifiers_and_rounding_fall_back(self):
        for question in ('What year was it?', 'Which article was it?', 'What is the phone number?', 'Round to two decimal places', 'Give the nearest integer'):
            with self.subTest(question=question): self.assertFallback(question,'12','12.0')


class UnitRules(Assertions, unittest.TestCase):
    def test_mass_scaling_and_attached_units(self):
        self.assertDecision('What is the mass?','2.75 kg','2750g',True)
        self.assertDecision('What is the mass?','2.75 kg','2750kg',False)
        self.assertDecision('What is the mass?','7000 micrograms','7mg',True)

    def test_requested_unit_inheritance(self):
        self.assertDecision('How many kilograms does it weigh?','4.2','4200 g',True)
        self.assertDecision('How many liters does it hold?','8','8 liters',True)

    def test_incidental_context_unit_is_not_requested_answer_unit(self):
        self.assertFallback('What amount is dissolved in a liter of water?', '7', '7 mL')
        self.assertFallback('What amount is dissolved in liters of water?', '7', '7 mL')
        self.assertDecision('How many liters of water are needed?', '7', '7 L', True)

    def test_no_unit_borrowed_from_reference(self):
        self.assertFallback('What is the measurement?','7 kg','7')
        self.assertFallback('What is the measurement?','7','7 kg')

    def test_mismatching_dimensions(self):
        self.assertDecision('How many liters does it hold?','3','3 kilograms',False)
        self.assertDecision('What is the quantity?','0 g','0 L',False)

    def test_reference_conflict_not_overruled(self):
        self.assertFallback('How many liters does it hold?','3 kg','3 kg')

    def test_length_and_area(self):
        self.assertDecision('What is the length?','2.5 meters','250 cm',True)
        self.assertDecision('What is the area?','0.04 m2','400 cm²',True)
        self.assertDecision('What is the measurement?','4 m','4 m2',False)

    def test_volume(self):
        self.assertDecision('What is the volume?','2.5 L','2500 mL',True)
        self.assertDecision('What is the volume?','1 m³','1000 L',True)
        self.assertDecision('What is the volume?','3 cubic centimeters','3 mL',True)

    def test_duration(self):
        self.assertDecision('How long?','1.5 hours','90 minutes',True)
        self.assertFallback('How long?','1 month','30 days')

    def test_parenthesis_alias_not_second_quantity(self):
        self.assertDecision('What is the volume?','7 mL','7 milliliters (mL)',True)
        self.assertFallback('What is the distance?','4 km','4 km (2.5 miles)')
        self.assertFallback('What is the volume?','7 mL','7 liters (mL)')

    def test_si_symbol_case(self):
        self.assertFallback('What is the volume?','2 mL','2 ML')
        self.assertFallback('What is the mass?','2 mg','2 MG')

    def test_unknown_units_and_rates_not_stripped(self):
        for candidate in ('4 gallons','4 tons','4 degrees C','4 widgets','4 kg per day','4 hours a week'):
            with self.subTest(candidate=candidate): self.assertFallback('What is the quantity?','4',candidate)

    def test_multiple_requested_units_defer(self):
        self.assertFallback('Give the value in cm or meters','2','2 cm')
        self.assertFallback('Give the value in cm and m','2','2 cm')
        self.assertFallback('How many kilograms per day?','2','2 kg')
        self.assertFallback('How many hours a week?','2','2 hours')
        self.assertFallback('How many meters squared?','2','2 meters')

    def test_explicit_currency_and_negative_balance(self):
        self.assertDecision('What is the price in US dollars?','USD 73','73 US dollars',True)
        self.assertDecision('What is the balance in US dollars?','-73','$73',False)
        self.assertDecision('What is the balance in US dollars?','-73','-$73',True)

    def test_no_foreign_exchange_or_assumed_dollar_currency(self):
        self.assertFallback('What is the price?','USD 73','$73')
        self.assertDecision('What is the amount?','USD 73','EUR 73',False)


class PercentageRules(Assertions, unittest.TestCase):
    def test_each_percent_sign_scales_its_own_value(self):
        self.assertDecision('What percentage was used?','40%','0.40%',False)
        self.assertDecision('What percentage was used?','40%','0.40 of the total',True)
        self.assertDecision('What percentage was used?','40%','40',True)
        self.assertDecision('What percentage was used?','40%','0.40',False)

    def test_fraction_question_context(self):
        self.assertDecision('What fraction was used?','3/8','37.5%',True)
        self.assertDecision('What fraction was used?','3/8','3.75%',False)

    def test_percent_format_request_does_not_change_quantity_policy(self):
        self.assertDecision('What fraction was used, expressed as a percentage?','12.5%','0.125 of the total',True)

    def test_no_percent_scale_assumed_without_context(self):
        self.assertFallback('What was the result?','12.5%','0.125')

    def test_percentage_points_defer(self):
        self.assertFallback('What was the increase?','5 percentage points','5%')
        self.assertFallback('What was the increase in percentage points?','5','5%')

    def test_negative_and_zero_percent(self):
        self.assertDecision('What percentage?','-20%','20%',False)
        self.assertDecision('What percentage?','0%','0 of the total',True)


class GeneralizationChecks(Assertions, unittest.TestCase):
    def test_generated_mass_pairs_and_scale_negatives(self):
        rng=random.Random(61291)
        for _ in range(120):
            amount=rng.randint(1,100000)
            with self.subTest(amount=amount):
                self.assertDecision('How many grams does it weigh?', str(amount), f'{amount*1000} mg', True)
                self.assertDecision('How many grams does it weigh?', str(amount), f'{amount*1000} g', False)

    def test_generated_percent_pairs_and_scale_negatives(self):
        rng=random.Random(94277)
        for _ in range(120):
            n=rng.randint(1,9900)
            # Compare rational spellings; no binary float calculation in test labels.
            self.assertDecision('What percentage?',f'{n}%',f'{n}/100 of the total',True)
            self.assertDecision('What percentage?',f'{n}%',f'{n}/100%',False)

    def test_symmetry_for_explicit_quantities(self):
        for left,right in [('8 kg','8000g'),('50%','1/2 of the total'),('1 m2','10000cm2'),('-2 EUR','EUR -2')]:
            self.assertDecision('What is the quantity?',left,right,True)
            self.assertDecision('What is the quantity?',right,left,True)

    def test_rules_do_not_call_legacy(self):
        def forbidden(): raise AssertionError('Legacy must not be called')
        result=hybrid_decide('How many kilograms?','4.2','4200g',forbidden)
        self.assertEqual(result['route'],'numeric_rules')
        self.assertTrue(result['decision'])

    def test_fallback_keeps_all_legacy_states(self):
        for status,decision in [('judged',True),('judged',False),('uncertain',None),('invalid',None)]:
            original={'status':status,'decision':decision,'reason':'unchanged'}
            result=hybrid_decide('Which place?','Test city','Test city district',lambda:deepcopy(original))
            self.assertEqual(result['legacy_result'],original)
            self.assertIs(result['decision'],decision)

    def test_wrong_numeric_value_is_not_overridden_by_legacy(self):
        def forbidden(): raise AssertionError('No fallback after a decisive mismatch')
        result=hybrid_decide('What percentage?','40%','0.4%',forbidden)
        self.assertIs(result['decision'],False)


if __name__=='__main__':
    unittest.main()

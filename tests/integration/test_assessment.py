from ddt import ddt, data, unpack
from .base_test import MentoringTest

CORRECT, INCORRECT, PARTIAL = "correct", "incorrect", "partially-correct"


class MentoringAssessmentBaseTest(MentoringTest):
    def _selenium_bug_workaround_scroll_to(self, mentoring):
        """Workaround for selenium bug:

        Some version of Selenium has a bug that prevents scrolling
        to radiobuttons before being clicked. The click not taking
        place, when it's outside the view.

        Since the bug does not affect other content, asking Selenium
        to click on the legend first, will properly scroll it.

        It also have it's fair share of issues with the workbench header.

        For this reason we click on the bottom-most element, scrolling to it.
        Then, click on the title of the question (also scrolling to it)
        hopefully, this gives us enough room for the full step with the
        control buttons to fit.
        """
        controls = mentoring.find_element_by_css_selector("div.submit")
        title = mentoring.find_element_by_css_selector("h3.question-title")
        self.scroll_to(controls)
        self.scroll_to(title)

    def assert_hidden(self, elem):
        self.assertFalse(elem.is_displayed())

    def assert_disabled(self, elem):
        self.assertTrue(elem.is_displayed())
        self.assertFalse(elem.is_enabled())

    def assert_clickable(self, elem):
        self.assertTrue(elem.is_displayed())
        self.assertTrue(elem.is_enabled())

    def assert_persistent_elements_present(self, mentoring):
        self.assertIn("A Simple Assessment", mentoring.text)
        self.assertIn("This paragraph is shared between all questions.", mentoring.text)

    def assert_disabled(self, elem):
        self.assertTrue(elem.is_displayed())
        self.assertFalse(elem.is_enabled())

    class _GetChoices(object):
        def __init__(self, mentoring, selector=".choices"):
            self._mcq = mentoring.find_element_by_css_selector(selector)

        @property
        def text(self):
            return self._mcq.text

        @property
        def state(self):
            return {
                choice.text: choice.find_element_by_css_selector("input").is_selected()
                for choice in self._mcq.find_elements_by_css_selector(".choice")}

        def select(self, text):
            state = {}
            for choice in self._mcq.find_elements_by_css_selector(".choice"):
                if choice.text == text:
                    choice.find_element_by_css_selector("input").click()
                    return
            raise AssertionError("Expected selectable item present: {}".format(text))

    def _assert_checkmark(self, mentoring, result):
        """Assert that only the desired checkmark is present."""
        states = {CORRECT: 0, INCORRECT: 0, PARTIAL: 0}
        states[result] += 1

        for name, count in states.items():
            self.assertEqual(len(mentoring.find_elements_by_css_selector(".checkmark-{}".format(name))), count)

    def go_to_assessment(self):
        mentoring = self.go_to_view("student_view")

        class Namespace(object):
            pass

        controls = Namespace()

        controls.submit = mentoring.find_element_by_css_selector("input.input-main")
        controls.next_question = mentoring.find_element_by_css_selector("input.input-next")
        controls.review = mentoring.find_element_by_css_selector("input.input-review")
        controls.try_again = mentoring.find_element_by_css_selector("input.input-try-again")
        controls.review_link = mentoring.find_element_by_css_selector(".review-link a")

        return mentoring, controls

    @staticmethod
    def question_text(number):
        if number:
            return "QUESTION %s" % number
        else:
            return "QUESTION"

    def freeform_answer(self, number, mentoring, controls, text_input, result, saved_value="", last=False):
        self.wait_until_text_in(self.question_text(number), mentoring)
        self.assert_persistent_elements_present(mentoring)
        self._selenium_bug_workaround_scroll_to(mentoring)

        answer = mentoring.find_element_by_css_selector("textarea.answer.editable")

        self.assertIn("Please answer the questions below.", mentoring.text)
        self.assertIn(self.question_text(number), mentoring.text)
        self.assertIn("What is your goal?", mentoring.text)

        self.assertEquals(saved_value, answer.get_attribute("value"))
        if not saved_value:
            self.assert_disabled(controls.submit)
        self.assert_disabled(controls.next_question)

        answer.clear()
        answer.send_keys(text_input)
        self.assertEquals(text_input, answer.get_attribute("value"))

        self.assert_clickable(controls.submit)
        self.ending_controls(controls, last)
        self.assert_hidden(controls.review)
        self.assert_hidden(controls.try_again)

        controls.submit.click()

        self.do_submit_wait(controls, last)
        self._assert_checkmark(mentoring, result)
        self.do_post(controls, last)

    def ending_controls(self, controls, last):
        if last:
            self.assert_hidden(controls.next_question)
            self.assert_disabled(controls.review)
        else:
            self.assert_disabled(controls.next_question)
            self.assert_hidden(controls.review)

    def selected_controls(self, controls, last):
        self.assert_clickable(controls.submit)
        if last:
            self.assert_hidden(controls.next_question)
            self.assert_disabled(controls.review)
        else:
            self.assert_disabled(controls.next_question)
            self.assert_hidden(controls.review)

    def do_submit_wait(self, controls, last):
        if last:
            self.wait_until_clickable(controls.review)
        else:
            self.wait_until_clickable(controls.next_question)

    def do_post(self, controls, last):
        if last:
            controls.review.click()
        else:
            controls.next_question.click()

    def just_select_on_a_single_choice_question(
            self, number, mentoring, controls, choice_name, last=False):
        self.wait_until_text_in(self.question_text(number), mentoring)
        self.assert_persistent_elements_present(mentoring)
        self._selenium_bug_workaround_scroll_to(mentoring)
        self.assertIn("Do you like this MCQ?", mentoring.text)

        self.assert_disabled(controls.submit)
        self.ending_controls(controls, last)
        self.assert_hidden(controls.try_again)

        choices = self._GetChoices(mentoring)
        expected_state = {"Yes": False, "Maybe not": False, "I don't understand": False}
        self.assertEquals(choices.state, expected_state)

        choices.select(choice_name)
        expected_state[choice_name] = True
        self.assertEquals(choices.state, expected_state)

        self.selected_controls(controls, last)

    def wait_for_and_check_single_choice_question_result(self, mentoring, controls, result, last=False):

        self.do_submit_wait(controls, last)
        self._assert_checkmark(mentoring, result)

        self.do_post(controls, last)

    def single_choice_question(self, number, mentoring, controls, choice_name, result, last=False):

        self.just_select_on_a_single_choice_question(
                number, mentoring, controls, choice_name, last)

        controls.submit.click()

        self.wait_for_and_check_single_choice_question_result(
                mentoring, controls, result, last)


    def answer_mcq(self, number, name, value, mentoring, controls, is_last=False):
        """ More generic version of single_choice_question """
        self.wait_until_text_in(self.question_text(number), mentoring)

        mentoring.find_element_by_css_selector('input[name={}][value={}]'.format(name, value)).click()
        self.selected_controls(controls, is_last)
        controls.submit.click()
        self.do_submit_wait(controls, is_last)
        self.do_post(controls, is_last)

    def rating_question(self, number, mentoring, controls, choice_name, result, last=False):
        self.wait_until_text_in(self.question_text(number), mentoring)
        self.assert_persistent_elements_present(mentoring)
        self._selenium_bug_workaround_scroll_to(mentoring)
        self.assertIn("How much do you rate this MCQ?", mentoring.text)

        self.assert_disabled(controls.submit)
        self.ending_controls(controls, last)
        self.assert_hidden(controls.review)
        self.assert_hidden(controls.try_again)

        choices = self._GetChoices(mentoring, ".rating")
        expected_choices = {
            "1 - Not good at all": False,
            "2": False, "3": False, "4": False,
            "5 - Extremely good": False,
            "I don't want to rate it": False,
        }
        self.assertEquals(choices.state, expected_choices)
        choices.select(choice_name)
        expected_choices[choice_name] = True
        self.assertEquals(choices.state, expected_choices)

        self.ending_controls(controls, last)

        controls.submit.click()

        self.do_submit_wait(controls, last)
        self._assert_checkmark(mentoring, result)
        self.do_post(controls, last)

    def peek_at_multiple_response_question(
            self, number, mentoring, controls, last=False, extended_feedback=False, alternative_review=False,
    ):
        self.wait_until_text_in(self.question_text(number), mentoring)
        self.assert_persistent_elements_present(mentoring)
        self._selenium_bug_workaround_scroll_to(mentoring)
        self.assertIn("What do you like in this MRQ?", mentoring.text)

        if extended_feedback:
            self.assert_disabled(controls.submit)
            if alternative_review:
                self.assert_clickable(controls.review_link)
                self.assert_hidden(controls.try_again)
            else:
                self.assert_clickable(controls.review)
        else:
            self.assert_disabled(controls.submit)
            self.ending_controls(controls, last)

    def multiple_response_question(self, number, mentoring, controls, choice_names, result, last=False):
        self.peek_at_multiple_response_question(number, mentoring, controls, last=last)

        choices = self._GetChoices(mentoring)
        expected_choices = {
            "Its elegance": False,
            "Its beauty": False,
            "Its gracefulness": False,
            "Its bugs": False,
        }
        self.assertEquals(choices.state, expected_choices)

        for name in choice_names:
            choices.select(name)
            expected_choices[name] = True

        self.assertEquals(choices.state, expected_choices)

        self.selected_controls(controls, last)

        controls.submit.click()

        self.do_submit_wait(controls, last)
        self._assert_checkmark(mentoring, result)
        controls.review.click()

    def peek_at_review(self, mentoring, controls, expected, extended_feedback=False):
        self.wait_until_text_in("You scored {percentage}% on this assessment".format(**expected), mentoring)
        self.assert_persistent_elements_present(mentoring)
        if expected["num_attempts"] < expected["max_attempts"]:
            self.assertIn("Note: if you retake this assessment, only your final score counts", mentoring.text)
            self.assertFalse(mentoring.find_elements_by_css_selector('.review-list'))
        elif extended_feedback:
            for q_type in ['correct', 'incorrect', 'partial']:
                self.assertEqual(len(mentoring.find_elements_by_css_selector('.%s-list li' % q_type)), expected[q_type])
        else:
            self.assertFalse(mentoring.find_elements_by_css_selector('.review-list'))
        self.assertIn("You answered {correct} questions correctly".format(**expected), mentoring.text)
        self.assertIn("You answered {partial} questions partially correct".format(**expected), mentoring.text)
        self.assertIn("You answered {incorrect} questions incorrectly".format(**expected), mentoring.text)
        self.assertIn("You have used {num_attempts} of {max_attempts} submissions".format(**expected), mentoring.text)

        self.assert_hidden(controls.submit)
        self.assert_hidden(controls.next_question)
        self.assert_hidden(controls.review)
        self.assert_hidden(controls.review_link)

    def assert_messages_text(self, mentoring, text):
        messages = mentoring.find_element_by_css_selector('.assessment-messages')
        self.assertEqual(messages.text, text)
        self.assertTrue(messages.is_displayed())

    def assert_messages_empty(self, mentoring):
        messages = mentoring.find_element_by_css_selector('.assessment-messages')
        self.assertEqual(messages.text, '')
        self.assertFalse(messages.find_elements_by_xpath('./*'))
        self.assertFalse(messages.is_displayed())

    def extended_feedback_checks(self, mentoring, controls, expected_results):
        # Multiple choice is third correctly answered question
        self.assert_hidden(controls.review_link)
        mentoring.find_elements_by_css_selector('.correct-list li a')[2].click()
        self.peek_at_multiple_response_question(4, mentoring, controls, extended_feedback=True, alternative_review=True)
        # Four correct items, plus the overall correct indicator.
        correct_marks = mentoring.find_elements_by_css_selector('.checkmark-correct')
        incorrect_marks = mentoring.find_elements_by_css_selector('.checkmark-incorrect')
        self.assertEqual(len(correct_marks), 5)
        self.assertEqual(len(incorrect_marks), 0)
        item_feedbacks = [
            "This is something everyone has to like about this MRQ",
            "This is something everyone has to like about this MRQ",
            "This MRQ is indeed very graceful",
            "Nah, there aren't any!"
        ]
        self.popup_check(mentoring, item_feedbacks, do_submit=False)
        self.assert_hidden(controls.review)
        self.assert_disabled(controls.submit)
        controls.review_link.click()
        self.peek_at_review(mentoring, controls, expected_results, extended_feedback=True)
        # Rating question, right before MRQ.
        mentoring.find_elements_by_css_selector('.incorrect-list li a')[0].click()
        # Should be possible to visit the MRQ from there.
        self.wait_until_clickable(controls.next_question)
        controls.next_question.click()
        self.peek_at_multiple_response_question(4, mentoring, controls, extended_feedback=True, alternative_review=True)


@ddt
class MentoringAssessmentTest(MentoringAssessmentBaseTest):

    @data((1, False), ('extended_feedback', True))
    @unpack
    def test_assessment(self, assessment, extended_feedback):
        self.load_scenario("assessment_{}.xml".format(assessment), load_immediately=False)
        mentoring, controls = self.go_to_assessment()

        self.freeform_answer(1, mentoring, controls, 'This is the answer', CORRECT)
        self.single_choice_question(2, mentoring, controls, 'Maybe not', INCORRECT)
        self.rating_question(3, mentoring, controls, "5 - Extremely good", CORRECT)
        self.peek_at_multiple_response_question(4, mentoring, controls, last=True)

        # see if assessment remembers the current step
        mentoring, controls = self.go_to_assessment()

        self.multiple_response_question(4, mentoring, controls, ("Its beauty",), PARTIAL, last=True)

        expected_results = {
                "correct": 2, "partial": 1, "incorrect": 1, "percentage": 63,
                "num_attempts": 1, "max_attempts": 2}
        self.peek_at_review(mentoring, controls, expected_results, extended_feedback=extended_feedback)
        self.assert_messages_text(mentoring, "Assessment additional feedback message text")
        self.assert_clickable(controls.try_again)
        controls.try_again.click()

        self.freeform_answer(1, mentoring, controls, 'This is a different answer', CORRECT,
                saved_value='This is the answer')
        self.single_choice_question(2, mentoring, controls, 'Yes', CORRECT)
        self.rating_question(3, mentoring, controls, "1 - Not good at all", INCORRECT)

        user_selection =  ("Its elegance", "Its beauty", "Its gracefulness")
        self.multiple_response_question(4, mentoring, controls, user_selection, CORRECT, last=True)

        expected_results = {
                "correct": 3, "partial": 0, "incorrect": 1, "percentage": 75,
                "num_attempts": 2, "max_attempts": 2}
        self.peek_at_review(mentoring, controls, expected_results, extended_feedback=extended_feedback)
        self.assert_disabled(controls.try_again)
        self.assert_messages_empty(mentoring)
        if extended_feedback:
            self.extended_feedback_checks(mentoring, controls, expected_results)


    def test_single_question_assessment(self):
        """
        No 'Next Question' button on single question assessment.
        """
        self.load_scenario("assessment_2.xml", load_immediately=False)
        mentoring, controls = self.go_to_assessment()
        self.single_choice_question(0, mentoring, controls, 'Maybe not', INCORRECT, last=True)

        expected_results = {
            "correct": 0, "partial": 0, "incorrect": 1, "percentage": 0,
            "num_attempts": 1, "max_attempts": 2}

        self.peek_at_review(mentoring, controls, expected_results)
        self.assert_messages_empty(mentoring)

        controls.try_again.click()
        # this is a wait and assertion all together - it waits until expected text is in mentoring block
        # and it fails with PrmoiseFailed exception if it's not
        self.wait_until_text_in(self.question_text(0), mentoring)

    def test_double_click_results_in_a_checkmark(self):
        """
        Double click on submit when selecting a proper response results in a green checkmark.
        """
        self.load_scenario("assessment_2.xml", load_immediately=False)
        mentoring, controls = self.go_to_assessment()

        self.just_select_on_a_single_choice_question(
                0, mentoring, controls, "Yes", True)

        controls.submit.click()
        controls.submit.click()

        self.wait_for_and_check_single_choice_question_result(
                mentoring, controls, CORRECT, True)

    def test_double_click_uses_only_a_single_attempt(self):
        """
        Double click on submit when selecting a wrong response uses only
        a single attempt
        """
        self.load_scenario("assessment_2.xml", load_immediately=False)
        mentoring, controls = self.go_to_assessment()

        self.just_select_on_a_single_choice_question(
                0, mentoring, controls, "Maybe not", True)

        controls.submit.click()
        controls.submit.click()

        self.do_submit_wait(controls, True)

        self.do_post(controls, True)

        expected_results = {
            "correct": 0, "partial": 0, "incorrect": 1, "percentage": 0,
            "num_attempts": 1, "max_attempts": 2}

        self.peek_at_review(mentoring, controls, expected_results)
        self.assert_messages_empty(mentoring)

"""
If an author makes changes to the block after students have started using it, will bad things
happen?
"""

from .base_test import MentoringTest
import ddt
from .test_assessment import MentoringAssessmentBaseTest
import re

class AuthorChangesTest(MentoringTest):
    """
    Test various scenarios involving author changes made to a block already in use by students
    """

    def setUp(self):
        super(AuthorChangesTest, self).setUp()
        self.load_scenario("author_changes.xml", {"mode": "standard", "use_intro": False}, load_immediately=False)
        self.refresh_page()

    def refresh_page(self):
        """
        [Re]load the page with our scenario
        """
        self.mentoring_dom = self.go_to_view("student_view")
        self.reload_mentoring_block()

    def reload_mentoring_block(self):
        """
        [Re]load the mentoring block, potentially with updated field data
        """
        vertical = self.load_root_xblock()
        self.mentoring = vertical.runtime.get_block(vertical.children[0])
        self.wait_until_text_in("QUESTION", self.mentoring_dom)

    def submit_answers(self, q1_answer='yes', q2_answer='elegance', q3_answer="It's boring."):
        """ Answer all three questions in the 'author_changes.xml' scenario correctly """
        self.mentoring_dom.find_element_by_css_selector('input[name=q1][value={}]'.format(q1_answer)).click()
        self.mentoring_dom.find_element_by_css_selector('input[name=q2][value={}]'.format(q2_answer)).click()
        self.mentoring_dom.find_element_by_css_selector('textarea').send_keys(q3_answer)
        self.click_submit(self.mentoring_dom)

    def set_xml_content(self, new_xml):
        """ Change the xml_content of self.mentoring """
        self.reload_mentoring_block()
        self.mentoring.xml_content = new_xml
        self.mentoring.save()
        self.reload_mentoring_block()

    def test_change_xml_cosmetic(self):
        """ Test that we make cosmetic changes to the XML without affecting student data: """
        self.assertEqual(self.mentoring.score.percentage, 0)  # Sanity/precondition check

        # First, submit an answer to each question
        self.submit_answers()

        self.reload_mentoring_block()
        orig_results = self.mentoring.student_results
        self.assertTrue(self.mentoring.student_results)  # sanity check - results should not be empty
        self.assertEqual(self.mentoring.score.percentage, 100)

        # Change the XML and refresh the page:
        self.assertEqual(self.mentoring_dom.text.count("don't you like"), 0)
        self.set_xml_content(self.mentoring.xml_content.replace("do you like", "don't you like"))
        self.refresh_page()
        self.assertEqual(self.mentoring_dom.text.count("don't you like"), 3)

        # Validate the student data:
        self.assertEqual(self.mentoring.student_results, orig_results)
        self.assertEqual(self.mentoring.score.percentage, 100)
        self.assertEqual(self.mentoring_dom.find_element_by_css_selector('textarea').text, "It's boring.")

    def test_delete_question(self):
        """ Test what the block behaves correctly when deleting a question """
        # First, submit an answer to each of the three questions, but get the second question wrong:
        self.submit_answers(q2_answer='bugs')
        self.reload_mentoring_block()
        self.assertEqual(self.mentoring.score.percentage, 67)

        # Delete Q2 (the MRQ)
        new_xml, changed = re.subn('<mrq name="q2">.*</mrq>', "", self.mentoring.xml_content, flags=re.DOTALL)
        self.assertEqual(changed, 1)
        self.set_xml_content(new_xml)

        # Now that the wrong question is deleted, the student should have a perfect score:
        self.assertEqual(self.mentoring.score.percentage, 100)
        # NOTE: This is questionable, since the block does not send a new 'grade' event to the
        # LMS. So the LMS 'grade' (based on the event sent when the student actually submitted
        # the answers) and the block's current 'score' may be different.

    def test_rename_question(self):
        """ Test what the block behaves correctly when renaming a question """
        # First, submit an answer to each of the three questions, but get the first question wrong:
        self.submit_answers(q1_answer='no')
        self.reload_mentoring_block()
        self.assertEqual(self.mentoring.score.percentage, 67)

        # Rename Q2 (the MRQ)
        new_xml, changed = re.subn('<mrq name="q2"', '<mrq name="newq2"', self.mentoring.xml_content)
        self.assertEqual(changed, 1)
        self.set_xml_content(new_xml)

        # Now verify that one question is wrong, one question unanswered, and one correct:
        self.assertEqual(self.mentoring.score.percentage, 33)

        # Now rename Q2 back:
        new_xml, changed = re.subn('<mrq name="newq2"', '<mrq name="q2"', self.mentoring.xml_content)
        self.assertEqual(changed, 1)
        self.set_xml_content(new_xml)
        # The score should now also be back to what it was:
        self.assertEqual(self.mentoring.score.percentage, 67)

    def test_reweight_question(self):
        """ Test what the block behaves correctly when changing the weight of a question """
        # First, submit an answer to each of the three questions, but get the first question wrong:
        self.submit_answers(q1_answer='no')
        self.reload_mentoring_block()
        self.assertEqual(self.mentoring.score.percentage, 67)

        # Re-weight Q1 to '5':
        self.mentoring.xml_content = self.mentoring.xml_content.replace(
            '<mcq name="q1"',
            '<mcq name="q1" weight="5"',
        )
        self.mentoring.save()
        self.reload_mentoring_block()
        self.assertEqual(self.mentoring.score.percentage, 29)  # 29% is 2 out of 7 (5+1+1)

        # Delete Q2 (the MRQ)
        new_xml, changed = re.subn('<mrq name="q2">.*</mrq>', "", self.mentoring.xml_content, flags=re.DOTALL)
        self.assertEqual(changed, 1)
        self.set_xml_content(new_xml)

        # Now, the student's score should be 1 out of 6 (only q3 is correct):
        self.assertEqual(self.mentoring.score.percentage, 17)


@ddt.ddt
class AuthorChangesAssessmentTest(MentoringAssessmentBaseTest):
    """
    Test various scenarios involving author changes made to an assessment block already in use
    """
    @ddt.data(True, False)
    def test_delete_question(self, use_extra_features):
        """ Test that the assessment behaves correctly when deleting a question. """
        self.load_scenario(
            "author_changes.xml",
            {"mode": "assessment", "use_intro": use_extra_features, "use_message": use_extra_features},
            load_immediately=False
        )
        mentoring, controls = self.go_to_assessment()

        # Answer each question, getting the first question wrong:
        self.answer_mcq(number=1, name="q1", value="no", mentoring=mentoring, controls=controls, is_last=False)
        mentoring, controls = self.go_to_assessment()
        self.answer_mcq(number=2, name="q2", value="elegance", mentoring=mentoring, controls=controls, is_last=False)

        mentoring.find_element_by_css_selector('textarea').send_keys("Hello world")
        controls.submit.click()
        self.wait_until_clickable(controls.review)
        controls.review.click()
        self.wait_until_hidden(controls.review)

        # Delete question 3:
        vertical = self.load_root_xblock()
        block = vertical.runtime.get_block(vertical.children[0])
        new_xml, changed = re.subn('<answer name="q3">.*</answer>', "", block.xml_content, flags=re.DOTALL)
        self.assertEqual(changed, 1)
        block.xml_content = new_xml
        block.save()

        mentoring, controls = self.go_to_assessment()

        self.assertIn("You scored 50% on this assessment.", mentoring.text)
        self.assertIn("You answered 1 questions correctly.", mentoring.text)
        self.assertIn("You answered 1 questions incorrectly.", mentoring.text)

        controls.try_again.click()
        self.wait_until_hidden(controls.try_again)

        # Now answer again, getting a perfect score:
        self.answer_mcq(number=1, name="q1", value="yes", mentoring=mentoring, controls=controls, is_last=False)
        self.answer_mcq(number=2, name="q2", value="elegance", mentoring=mentoring, controls=controls, is_last=True)
        self.assertIn("You scored 100% on this assessment.", mentoring.text)

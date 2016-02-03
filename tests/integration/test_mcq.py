# -*- coding: utf-8 -*-
#
# Copyright (C) 2014 Harvard
#
# Authors:
#          Xavier Antoviaque <xavier@antoviaque.org>
#
# This software's license gives you freedom; you can copy, convey,
# propagate, redistribute and/or modify this program under the terms of
# the GNU Affero General Public License (AGPL) as published by the Free
# Software Foundation (FSF), either version 3 of the License, or (at your
# option) any later version of the AGPL published by the FSF.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero
# General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program in a file in the toplevel directory called
# "AGPLv3".  If not, see <http://www.gnu.org/licenses/>.
#

# Imports ###########################################################
import ddt
from .base_test import MentoringBaseTest


# Classes ###########################################################


@ddt.ddt
class MCQBlockTest(MentoringBaseTest):

    def _selenium_bug_workaround_scroll_to(self, mcq_legend):
        """Workaround for selenium bug:

        Some version of Selenium has a bug that prevents scrolling
        to radiobuttons before being clicked. The click not taking
        place, when it's outside the view.

        Since the bug does not affect other content, asking Selenium
        to click on the legend first, will properly scroll it.
        """
        self.scroll_to(mcq_legend)

    def _get_labels(self, choices):
        return [choice.find_element_by_css_selector('label') for choice in choices]

    def _get_inputs(self, choices):
        return [choice.find_element_by_css_selector('input') for choice in choices]

    def assert_messages_empty(self, messages):
        self.assertEqual(messages.text, '')
        self.assertFalse(messages.find_elements_by_xpath('./*'))

    def test_mcq_choices_rating(self):
        """
        Mentoring MCQ should display tips according to user choice
        """
        # Initial MCQ status
        mentoring = self.go_to_page('Mcq 1')
        mcq1 = mentoring.find_element_by_css_selector('fieldset.choices')
        mcq2 = mentoring.find_element_by_css_selector('fieldset.rating')
        messages = mentoring.find_element_by_css_selector('.messages')
        submit = mentoring.find_element_by_css_selector('.submit input.input-main')

        self.assert_messages_empty(messages)
        self.assertFalse(submit.is_enabled())

        mcq1_legend = mcq1.find_element_by_css_selector('legend')
        mcq2_legend = mcq2.find_element_by_css_selector('legend')
        self.assertEqual(mcq1_legend.text, 'QUESTION 1\nDo you like this MCQ?')
        self.assertEqual(mcq2_legend.text, 'QUESTION 2\nHow much do you rate this MCQ?')

        mcq1_choices = mcq1.find_elements_by_css_selector('.choices .choice')
        mcq2_choices = mcq2.find_elements_by_css_selector('.rating .choice')

        self.assertEqual(len(mcq1_choices), 3)
        self.assertEqual(len(mcq2_choices), 6)

        mcq1_choices_label = self._get_labels(mcq1_choices)
        mcq2_choices_label = self._get_labels(mcq2_choices)

        self.assertEqual(mcq1_choices_label[0].text, 'Yes')
        self.assertEqual(mcq1_choices_label[1].text, 'Maybe not')
        self.assertEqual(mcq1_choices_label[2].text, "I don't understand")
        self.assertEqual(mcq2_choices_label[0].text, '1 - Not good at all')
        self.assertEqual(mcq2_choices_label[1].text, '2')
        self.assertEqual(mcq2_choices_label[2].text, '3')
        self.assertEqual(mcq2_choices_label[3].text, '4')
        self.assertEqual(mcq2_choices_label[4].text, '5 - Extremely good')
        self.assertEqual(mcq2_choices_label[5].text, "I don't want to rate it")

        mcq1_choices_input = self._get_inputs(mcq1_choices)
        mcq2_choices_input = self._get_inputs(mcq2_choices)

        self.assertEqual(mcq1_choices_input[0].get_attribute('value'), 'yes')
        self.assertEqual(mcq1_choices_input[1].get_attribute('value'), 'maybenot')
        self.assertEqual(mcq1_choices_input[2].get_attribute('value'), 'understand')
        self.assertEqual(mcq2_choices_input[0].get_attribute('value'), '1')
        self.assertEqual(mcq2_choices_input[1].get_attribute('value'), '2')
        self.assertEqual(mcq2_choices_input[2].get_attribute('value'), '3')
        self.assertEqual(mcq2_choices_input[3].get_attribute('value'), '4')
        self.assertEqual(mcq2_choices_input[4].get_attribute('value'), '5')
        self.assertEqual(mcq2_choices_input[5].get_attribute('value'), 'notwant')

        # Submit button disabled without selecting anything
        self.assertFalse(submit.is_enabled())

        # Submit button stays disabled when there are unfinished mcqs
        self._selenium_bug_workaround_scroll_to(mcq1)
        mcq1_choices_input[1].click()
        self.assertFalse(submit.is_enabled())

        # Should not show full completion message when wrong answers are selected
        self._selenium_bug_workaround_scroll_to(mcq1)
        mcq1_choices_input[0].click()
        mcq2_choices_input[2].click()
        self.assertTrue(submit.is_enabled())
        submit.click()
        self.wait_until_disabled(submit)

        self.assertEqual(mcq1.find_element_by_css_selector(".feedback").text, 'Great!')
        self.assertEqual(mcq2.find_element_by_css_selector(".feedback").text, 'Will do better next time...')
        self.assertEqual(messages.text, '')
        self.assertFalse(messages.is_displayed())

        # Should show full completion when the right answers are selected
        self._selenium_bug_workaround_scroll_to(mcq1)
        mcq1_choices_input[0].click()
        mcq2_choices_input[3].click()
        self.assertTrue(submit.is_enabled())
        submit.click()
        self.wait_until_disabled(submit)

        self.assertEqual(mcq1.find_element_by_css_selector(".feedback").text, 'Great!')
        self.assertEqual(mcq2.find_element_by_css_selector(".feedback").text, 'I love good grades.')
        self.assertIn('All is good now...\nCongratulations!', messages.text)
        self.assertTrue(messages.is_displayed())

    def test_mcq_with_comments(self):
        mentoring = self.go_to_page('Mcq With Comments 1')
        mcq = mentoring.find_element_by_css_selector('fieldset.choices')
        messages = mentoring.find_element_by_css_selector('.messages')
        submit = mentoring.find_element_by_css_selector('.submit input.input-main')

        self.assertEqual(messages.text, '')
        self.assertFalse(messages.find_elements_by_xpath('./*'))
        self.assertFalse(submit.is_enabled())

        mcq_legend = mcq.find_element_by_css_selector('legend')
        self.assertEqual(mcq_legend.text, 'QUESTION\nWhat do you like in this MRQ?')

        mcq_choices = mcq.find_elements_by_css_selector('.choices .choice')

        self.assertEqual(len(mcq_choices), 4)

        mcq_choices_label = self._get_labels(mcq_choices)

        self.assertEqual(mcq_choices_label[0].text, 'Its elegance')
        self.assertEqual(mcq_choices_label[1].text, 'Its beauty')
        self.assertEqual(mcq_choices_label[2].text, "Its gracefulness")
        self.assertEqual(mcq_choices_label[3].text, "Its bugs")

        mcq_choices_input = self._get_inputs(mcq_choices)
        self.assertEqual(mcq_choices_input[0].get_attribute('value'), 'elegance')
        self.assertEqual(mcq_choices_input[1].get_attribute('value'), 'beauty')
        self.assertEqual(mcq_choices_input[2].get_attribute('value'), 'gracefulness')
        self.assertEqual(mcq_choices_input[3].get_attribute('value'), 'bugs')

    @ddt.data(
        'Mcq Without Title',
        'Mcq Rating Without Title',
        'Mrq Without Title'
    )
    def test_mcq_without_title(self, page):
        mentoring = self.go_to_page(page)
        mcq_legend = mentoring.find_element_by_css_selector('fieldset legend')
        self.assertNotIn('QUESTION', mcq_legend.text)

    def test_mcq_feedback_popups(self):
        mentoring = self.go_to_page('Mcq With Comments 1')
        item_feedbacks = [
            "This is something everyone has to like about this MRQ",
            "This is something everyone has to like about beauty",
            "This MRQ is indeed very graceful",
            "Nah, there aren\\'t any!"
        ]
        self.popup_check(mentoring, item_feedbacks)

    def _get_questionnaire_options(self, questionnaire):
        result = []
        # this could be a list comprehension, but a bit complicated one - hence explicit loop
        for choice_wrapper in questionnaire.find_elements_by_css_selector(".choice"):
            choice_label = choice_wrapper.find_element_by_css_selector(".choice-label .choice-text")
            light_child = choice_label.find_element_by_css_selector(".xblock-light-child")
            result.append(light_child.find_element_by_css_selector("div").get_attribute('innerHTML'))

        return result

    @ddt.data(
        'Mrq With Html Choices',
        'Mcq With Html Choices'
    )
    def test_questionnaire_html_choices(self, page):
        mentoring = self.go_to_page(page)
        choices_list = mentoring.find_element_by_css_selector(".choices-list")
        scenario_title = mentoring.find_element_by_css_selector('h2.main')
        messages = mentoring.find_element_by_css_selector('.messages')

        expected_options = [
            "<b>Its elegance</b>",
            "<i>Its beauty</i>",
            "<strong>Its gracefulness</strong>",
            '<span style="font-color:red">Its bugs</span>'
        ]

        options = self._get_questionnaire_options(choices_list)
        self.assertEqual(expected_options, options)

        self.assert_messages_empty(messages)

        submit = mentoring.find_element_by_css_selector('.submit input.input-main')
        self.assertFalse(submit.is_enabled())

        inputs = choices_list.find_elements_by_css_selector('.choice-selector input')
        self._selenium_bug_workaround_scroll_to(scenario_title)
        inputs[0].click()
        inputs[1].click()
        inputs[2].click()

        self.assertTrue(submit.is_enabled())
        submit.click()
        self.wait_until_disabled(submit)

        self.assertIn('Congratulations!', messages.text)

    def _get_inner_height(self, elem):
        return elem.size['height'] - \
            int(elem.value_of_css_property("padding-top").replace(u'px', u'')) - \
            int(elem.value_of_css_property("padding-bottom").replace(u'px', u''))

    @ddt.unpack
    @ddt.data(
        ('yes', 40),
        ('maybenot', 60),
        ('understand', 600)
    )
    def test_tip_height(self, choice_value, expected_height):
        mentoring = self.go_to_page("Mcq With Fixed Height Tips")
        choices_list = mentoring.find_element_by_css_selector(".choices-list")
        submit = mentoring.find_element_by_css_selector('.submit input.input-main')
        feedback = choices_list.find_element_by_css_selector(".feedback")

        choice_input_css_selector = ".choice .choice-selector input[value={}]".format(choice_value)
        choice_input = choices_list.find_element_by_css_selector(choice_input_css_selector)
        choice_wrapper = choice_input.find_element_by_xpath("./ancestor::div[@class='choice']")

        choice_input.click()
        self.wait_until_clickable(submit)
        submit.click()
        self.wait_until_visible(feedback)
        feedback_height = self._get_inner_height(feedback)
        self.assertEqual(feedback_height, expected_height)

        choice_wrapper.find_element_by_css_selector(".choice-result").click()
        item_feedback_height = self._get_inner_height(choice_wrapper.find_element_by_css_selector(".choice-tips"))
        self.assertEqual(item_feedback_height, expected_height)

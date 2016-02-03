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
"""
Base classes for mentoring XBlock integration tests
"""

from xblockutils.base_test import SeleniumBaseTest, SeleniumXBlockTest
from xblockutils.resources import ResourceLoader

loader = ResourceLoader(__name__)


class PopupCheckMixin(object):
    """
    Helper method used by both test base classes
    """
    def popup_check(self, mentoring, item_feedbacks, do_submit=True):
        """
        Helper method for checking the tip popups given for a particular choice
        """
        choices_list = mentoring.find_element_by_css_selector(".choices-list")

        submit = mentoring.find_element_by_css_selector('.submit input.input-main')

        scenario_title = mentoring.find_element_by_css_selector('h2.main')

        question_title = mentoring.find_element_by_css_selector('h3.question-title')

        for index, expected_feedback in enumerate(item_feedbacks):
            choice_wrapper = choices_list.find_elements_by_css_selector(".choice")[index]
            if do_submit:
                # click on actual radio button:
                choice_wrapper.find_element_by_css_selector(".choice-selector input").click()
                submit.click()
                self.wait_until_exists('.choice-result.checkmark-incorrect,.choice-result.checkmark-correct')
            item_feedback_icon = choice_wrapper.find_element_by_css_selector(".choice-result")
            # choice_wrapper.click()
            item_feedback_icon.click()  # clicking on item feedback icon
            item_feedback_popup = choice_wrapper.find_element_by_css_selector(".choice-tips")
            self.wait_until_text_in(expected_feedback, item_feedback_popup)
            self.assertTrue(item_feedback_popup.is_displayed())

            item_feedback_popup.click()
            self.assertTrue(item_feedback_popup.is_displayed())

            self.driver.execute_script("return arguments[0].scrollIntoView();", scenario_title)
            question_title.click()
            self.wait_until_hidden(item_feedback_popup)


class MentoringTest(SeleniumXBlockTest, PopupCheckMixin):
    """
    The new base class for integration tests.
    Scenarios can be loaded and edited on the fly.
    """
    default_css_selector = 'div.mentoring'

    def load_scenario(self, xml_file, params=None, load_immediately=True):
        """
        Given the name of an XML file in the xml_templates folder, load it into the workbench.
        """
        params = params or {}
        scenario = loader.render_template("xml_templates/{}".format(xml_file), params)
        self.set_scenario_xml(scenario)
        if load_immediately:
            return self.go_to_view("student_view")

    def click_submit(self, mentoring):
        """ Click the submit button and wait for the response """
        submit = mentoring.find_element_by_css_selector('.submit input.input-main')
        self.assertTrue(submit.is_displayed())
        self.assertTrue(submit.is_enabled())
        self.driver.execute_script("return window.scrollTo(0, arguments[0]-300);", submit.location['y'])
        submit.click()
        self.wait_until_disabled(submit)


class MentoringBaseTest(SeleniumBaseTest, PopupCheckMixin):
    """
    Old-style way of implementing Selenium integration tests.
    Loads all scenarios from tests/integration/xml/ into the workbench.
    """
    module_name = __name__
    default_css_selector = 'div.mentoring'

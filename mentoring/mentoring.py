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

import json
import logging
import uuid
import re

from collections import namedtuple

from lxml import etree
from StringIO import StringIO

from xblock.core import XBlock
from xblock.fields import Boolean, Scope, String, Integer, Float, List
from xblock.fragment import Fragment

from .light_children import XBlockWithLightChildren
from .title import TitleBlock
from .header import SharedHeaderBlock
from .message import MentoringMessageBlock
from .step import StepParentMixin
from .utils import loader


# Globals ###########################################################

log = logging.getLogger(__name__)


def _default_xml_content():
    return loader.render_template(
        'templates/xml/mentoring_default.xml',
        {'url_name': 'mentoring-{}'.format(uuid.uuid4())})


def _is_default_xml_content(value):
    UUID_PATTERN = '[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}'
    DUMMY_UUID = '12345678-1234-1234-1234-123456789abc'

    expected = _default_xml_content()

    expected = re.sub(UUID_PATTERN, DUMMY_UUID, expected)
    value = re.sub(UUID_PATTERN, DUMMY_UUID, value)

    return value == expected


# Classes ###########################################################

Score = namedtuple("Score", ["raw", "percentage", "correct", "incorrect", "partially_correct"])

CORRECT = 'correct'
INCORRECT = 'incorrect'
PARTIAL = 'partial'


class MentoringBlock(XBlockWithLightChildren, StepParentMixin):
    """
    An XBlock providing mentoring capabilities

    Composed of text, answers input fields, and a set of MRQ/MCQ with advices.
    A set of conditions on the provided answers and MCQ/MRQ choices will determine if the
    student is a) provided mentoring advices and asked to alter his answer, or b) is given the
    ok to continue.
    """

    @staticmethod
    def is_default_xml_content(value):
        return _is_default_xml_content(value)

    attempted = Boolean(help="Has the student attempted this mentoring step?",
                        default=False, scope=Scope.user_state)
    completed = Boolean(help="Has the student completed this mentoring step?",
                        default=False, scope=Scope.user_state)
    next_step = String(help="url_name of the next step the student must complete (global to all blocks)",
                       default='mentoring_first', scope=Scope.preferences)
    followed_by = String(help="url_name of the step after the current mentoring block in workflow",
                         default=None, scope=Scope.content)
    url_name = String(help="Name of the current step, used for URL building",
                      default='mentoring-default', scope=Scope.content)
    enforce_dependency = Boolean(help="Should the next step be the current block to complete?",
                                 default=False, scope=Scope.content, enforce_type=True)
    display_submit = Boolean(help="Allow submission of the current block?", default=True,
                             scope=Scope.content, enforce_type=True)
    xml_content = String(help="XML content", default=_default_xml_content, scope=Scope.content)
    weight = Float(help="Defines the maximum total grade of the block.",
                   default=1, scope=Scope.content, enforce_type=True)
    num_attempts = Integer(help="Number of attempts a user has answered for this questions",
                           default=0, scope=Scope.user_state, enforce_type=True)
    max_attempts = Integer(help="Number of max attempts for this questions", default=0,
                           scope=Scope.content, enforce_type=True)
    mode = String(help="Mode of the mentoring. 'standard' or 'assessment'",
                  default='standard', scope=Scope.content)
    step = Integer(help="Keep track of the student assessment progress.",
                   default=0, scope=Scope.user_state, enforce_type=True)
    student_results = List(help="Store results of student choices.", default=[],
                           scope=Scope.user_state)
    extended_feedback = Boolean(help="Show extended feedback details when all attempts are used up.",
                                default=False, Scope=Scope.content)
    display_name = String(help="Display name of the component", default="Mentoring XBlock",
                          scope=Scope.settings)
    icon_class = 'problem'
    has_score = True

    MENTORING_MODES = ('standard', 'assessment')

    FLOATING_BLOCKS = (TitleBlock, MentoringMessageBlock, SharedHeaderBlock)

    FIELDS_TO_INIT = ('xml_content',)

    @property
    def is_assessment(self):
        return self.mode == 'assessment'

    def get_question_number(self, question_id):
        """
        Get the step number of the question id
        """
        for question in self.get_children_objects():
            if hasattr(question, 'step_number') and (question.name == question_id):
                return question.step_number
        raise ValueError("Question ID in answer set not a step of this Mentoring Block!")

    def answer_mapper(self, answer_status):
        """
        Create a JSON-dumpable object with readable key names from a list of student answers.
        """
        answer_map = []
        for answer in self.student_results:
            if answer[1]['status'] == answer_status:
                try:
                    answer_map.append({
                        'number': self.get_question_number(answer[0]),
                        'id': answer[0],
                        'details': answer[1],
                    })
                except ValueError:
                    pass
        return answer_map

    @property
    def score(self):
        """Compute the student score taking into account the light child weight."""
        total_child_weight = sum(float(step.weight) for step in self.steps)
        if total_child_weight == 0:
            return Score(0, 0, [], [], [])
        score = sum(r[1]['score'] * r[1]['weight'] for r in self.student_results) / total_child_weight
        correct = self.answer_mapper(CORRECT)
        incorrect = self.answer_mapper(INCORRECT)
        partially_correct = self.answer_mapper(PARTIAL)

        return Score(score, int(round(score * 100)), correct, incorrect, partially_correct)

    @property
    def assessment_message(self):
        if not self.max_attempts_reached:
            return self.get_message_html('on-assessment-review')
        else:
            return None

    def show_extended_feedback(self):
        return self.extended_feedback and self.max_attempts_reached

    def feedback_dispatch(self, target_data, stringify):
        if self.show_extended_feedback():
            if stringify:
                return json.dumps(target_data)
            else:
                return target_data

    def correct_json(self, stringify=True):
        return self.feedback_dispatch(self.score.correct, stringify)

    def incorrect_json(self, stringify=True):
        return self.feedback_dispatch(self.score.incorrect, stringify)

    def partial_json(self, stringify=True):
        return self.feedback_dispatch(self.score.partially_correct, stringify)

    def student_view(self, context):
        # Migrate stored data if necessary
        self.migrate_fields()

        fragment, named_children = self.get_children_fragment(
            context, view_name='mentoring_view',
            not_instance_of=self.FLOATING_BLOCKS,
        )

        fragment.add_content(loader.render_template('templates/html/mentoring.html', {
            'self': self,
            'named_children': named_children,
            'missing_dependency_url': self.has_missing_dependency and self.next_step_url,
        }))
        fragment.add_css_url(self.runtime.local_resource_url(self, 'public/css/mentoring.css'))
        fragment.add_javascript_url(
            self.runtime.local_resource_url(self, 'public/js/vendor/underscore-min.js'))

        js_view = 'mentoring_assessment_view.js' if self.is_assessment else 'mentoring_standard_view.js'
        fragment.add_javascript_url(self.runtime.local_resource_url(self, 'public/js/'+js_view))

        fragment.add_javascript_url(self.runtime.local_resource_url(self, 'public/js/mentoring.js'))
        fragment.add_resource(loader.load_unicode('templates/html/mentoring_attempts.html'), "text/html")
        fragment.add_resource(loader.load_unicode('templates/html/mentoring_grade.html'), "text/html")
        fragment.add_resource(loader.load_unicode('templates/html/mentoring_review_questions.html'), "text/html")

        fragment.initialize_js('MentoringBlock')

        if not self.display_submit:
            self.runtime.publish(self, 'progress', {})

        return fragment

    def migrate_fields(self):
        """
        Migrate data stored in the fields, when a format change breaks backward-compatibility with
        previous data formats
        """
        # Partial answers replaced the `completed` with `status` in `self.student_results`
        if self.student_results and 'completed' in self.student_results[0][1]:
            # Rename the field and use the new value format (text instead of boolean)
            for result in self.student_results:
                result[1]['status'] = CORRECT if result[1]['completed'] else INCORRECT
                del result[1]['completed']

    @property
    def additional_publish_event_data(self):
        return {
            'user_id': self.scope_ids.user_id,
            'component_id': self.url_name,
        }

    @property
    def title(self):
        """
        Returns the title child.
        """
        for child in self.get_children_objects():
            if isinstance(child, TitleBlock):
                return child
        return None

    @property
    def header(self):
        """
        Return the header child.
        """
        for child in self.get_children_objects():
            if isinstance(child, SharedHeaderBlock):
                return child
        return None

    @property
    def has_missing_dependency(self):
        """
        Returns True if the student needs to complete another step before being able to complete
        the current one, and False otherwise
        """
        return self.enforce_dependency and (not self.completed) and (self.next_step != self.url_name)

    @property
    def next_step_url(self):
        """
        Returns the URL of the next step's page
        """
        return '/jump_to_id/{}'.format(self.next_step)

    @XBlock.json_handler
    def get_results(self, queries, suffix=''):
        """
        Gets detailed results in the case of extended feedback.

        It may be a good idea to eventually have this function get results
        in the general case instead of loading them in the template in the future,
        and only using it for extended feedback situations.

        Right now there are two ways to get results-- through the template upon loading up
        the mentoring block, or after submission of an AJAX request like in
        submit or get_results here.
        """
        results = []
        if not self.show_extended_feedback():
            return {
                'results': [],
                'error': 'Extended feedback results cannot be obtained.'
            }
        completed = True
        choices = dict(self.student_results)
        step = self.step
        # Only one child should ever be of concern with this method.
        for child in self.get_children_objects():
            if child.name and child.name in queries:
                results = [child.name, child.get_results(choices[child.name])]
                # Children may have their own definition of 'completed' which can vary from the general case
                # of the whole mentoring block being completed. This is because in standard mode, all children
                # must be correct to complete the block. In assessment mode with extended feedback, completion
                # happens when you're out of attempts, no matter how you did.
                completed = choices[child.name]['status']
                break

        # The 'completed' message should always be shown in this case, since no more attempts are available.
        message = self.get_message(True)

        return {
            'results': results,
            'completed': completed,
            'attempted': self.attempted,
            'message': message,
            'step': step,
            'max_attempts': self.max_attempts,
            'num_attempts': self.num_attempts,
        }

    def get_message(self, completed):
        if self.max_attempts_reached:
            return self.get_message_html('max_attempts_reached')
        elif completed:
            return self.get_message_html('completed')
        else:
            return self.get_message_html('incomplete')

    @XBlock.json_handler
    def submit(self, submissions, suffix=''):
        log.info(u'Received submissions: {}'.format(submissions))
        self.attempted = True

        if self.is_assessment:
            return self.handleAssessmentSubmit(submissions, suffix)

        submit_results = []
        completed = True
        for child in self.get_children_objects():
            if child.name and child.name in submissions:
                submission = submissions[child.name]
                child_result = child.submit(submission)
                submit_results.append([child.name, child_result])
                child.save()
                completed = completed and (child_result['status'] == CORRECT)

        message = self.get_message(completed)

        # Once it has been completed once, keep completion even if user changes values
        if self.completed:
            completed = True

        # server-side check to not set completion if the max_attempts is reached
        if self.max_attempts_reached:
            completed = False

        if self.has_missing_dependency:
            completed = False
            message = 'You need to complete all previous steps before being able to complete the current one.'
        elif completed and self.next_step == self.url_name:
            self.next_step = self.followed_by

        # Once it was completed, lock score
        if not self.completed:
            # save user score and results
            while self.student_results:
                self.student_results.pop()
            for result in submit_results:
                self.student_results.append(result)

            self.runtime.publish(self, 'grade', {
                'value': self.score.raw,
                'max_value': 1,
            })

        if not self.completed and self.max_attempts > 0:
            self.num_attempts += 1

        self.completed = completed is True

        raw_score = self.score.raw

        self.publish_event_from_dict('xblock.mentoring.submitted', {
            'num_attempts': self.num_attempts,
            'submitted_answer': submissions,
            'grade': raw_score,
        })

        return {
            'results': submit_results,
            'completed': self.completed,
            'attempted': self.attempted,
            'message': message,
            'max_attempts': self.max_attempts,
            'num_attempts': self.num_attempts
        }

    def handleAssessmentSubmit(self, submissions, suffix):
        completed = False
        current_child = None
        children = [child for child in self.get_children_objects()
                    if not isinstance(child, self.FLOATING_BLOCKS)]

        assessment_message = None

        for child in children:
            if child.name and child.name in submissions:
                submission = submissions[child.name]

                # Assessment mode doesn't allow to modify answers
                # This will get the student back at the step he should be
                current_child = child
                step = children.index(child)
                if self.step > step or self.max_attempts_reached:
                    step = self.step
                    completed = False
                    break

                self.step = step + 1

                child_result = child.submit(submission)
                if 'tips' in child_result:
                    del child_result['tips']
                self.student_results.append([child.name, child_result])
                child.save()
                completed = child_result['status']

        event_data = {}

        score = self.score

        if current_child == self.steps[-1]:
            log.info(u'Last assessment step submitted: {}'.format(submissions))
            if not self.max_attempts_reached:
                self.runtime.publish(self, 'grade', {
                    'value': score.raw,
                    'max_value': 1,
                    'score_type': 'proficiency',
                })
                event_data['final_grade'] = score.raw
                assessment_message = self.assessment_message

            self.num_attempts += 1
            self.completed = True

        event_data['exercise_id'] = current_child.name
        event_data['num_attempts'] = self.num_attempts
        event_data['submitted_answer'] = submissions

        self.publish_event_from_dict('xblock.mentoring.assessment.submitted', event_data)

        return {
            'completed': completed,
            'attempted': self.attempted,
            'max_attempts': self.max_attempts,
            'num_attempts': self.num_attempts,
            'step': self.step,
            'score': score.percentage,
            'correct_answer': len(score.correct),
            'incorrect_answer': len(score.incorrect),
            'partially_correct_answer': len(score.partially_correct),
            'extended_feedback': self.show_extended_feedback() or '',
            'correct': self.correct_json(stringify=False),
            'incorrect': self.incorrect_json(stringify=False),
            'partial': self.partial_json(stringify=False),
            'assessment_message': assessment_message,
        }

    @XBlock.json_handler
    def try_again(self, data, suffix=''):

        if self.max_attempts_reached:
            return {
                'result': 'error',
                'message': 'max attempts reached'
            }

        # reset
        self.step = 0
        self.completed = False

        while self.student_results:
            self.student_results.pop()

        return {
            'result': 'success'
        }

    @property
    def max_attempts_reached(self):
        return self.max_attempts > 0 and self.num_attempts >= self.max_attempts

    def get_message_fragment(self, message_type):
        for child in self.get_children_objects():
            if isinstance(child, MentoringMessageBlock) and child.type == message_type:
                frag = self.render_child(child, 'mentoring_view', {})
                return self.fragment_text_rewriting(frag)

    def get_message_html(self, message_type):
        fragment = self.get_message_fragment(message_type)
        if fragment:
            return fragment.body_html()
        else:
            return ''

    def studio_view(self, context):
        """
        Editing view in Studio
        """
        fragment = Fragment()
        fragment.add_content(loader.render_template('templates/html/mentoring_edit.html', {
            'self': self,
            'xml_content': self.xml_content,
        }))
        fragment.add_javascript_url(
            self.runtime.local_resource_url(self, 'public/js/mentoring_edit.js'))
        fragment.add_css_url(
            self.runtime.local_resource_url(self, 'public/css/mentoring_edit.css'))

        fragment.initialize_js('MentoringEditBlock')

        return fragment

    @XBlock.json_handler
    def studio_submit(self, submissions, suffix=''):
        log.info(u'Received studio submissions: {}'.format(submissions))

        xml_content = submissions['xml_content']
        try:
            content = etree.parse(StringIO(xml_content))
        except etree.XMLSyntaxError as e:
            response = {
                'result': 'error',
                'message': e.message
            }

        else:
            success = True
            root = content.getroot()
            if 'mode' in root.attrib:
                if root.attrib['mode'] not in self.MENTORING_MODES:
                    response = {
                        'result': 'error',
                        'message': "Invalid mentoring mode: should be 'standard' or 'assessment'"
                    }
                    success = False
                elif root.attrib['mode'] == 'assessment' and 'max_attempts' not in root.attrib:
                    # assessment has a default of 2 max_attempts
                    root.attrib['max_attempts'] = '2'

            if success:
                response = {
                    'result': 'success',
                }
                self.xml_content = etree.tostring(content, pretty_print=True)

        log.debug(u'Response from Studio: {}'.format(response))
        return response

    @property
    def url_name_with_default(self):
        """
        Ensure the `url_name` is set to a unique, non-empty value.
        This should ideally be handled by Studio, but we need to declare the attribute
        to be able to use it from the workbench, and when this happen Studio doesn't set
        a unique default value - this property gives either the set value, or if none is set
        a randomized default value
        """
        if self.url_name == 'mentoring-default':
            return 'mentoring-{}'.format(uuid.uuid4())
        else:
            return self.url_name

    @staticmethod
    def workbench_scenarios():
        """
        Scenarios displayed by the workbench. Load them from external (private) repository
        """
        return loader.load_scenarios_from_path('templates/xml')

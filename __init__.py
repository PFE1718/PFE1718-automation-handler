# Copyright 2018 Adrien CHEVRIER, Florian HEPP, Xavier HERMAND,
#                Gauthier LEONARD, Audrey LY, Elliot MAINCOURT
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Import statements
import json

from os import makedirs, remove, listdir, path
from os.path import dirname, join, exists, expanduser, isfile, abspath

from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill
from mycroft.skills.core import intent_handler
from mycroft.skills.context import adds_context, removes_context
from mycroft.util.log import getLogger, LOG

__author__ = 'mouponlee'

# Logger: used for debug lines, like "LOGGER.debug(xyz)". These
# statements will show up in the command line when running Mycroft.
LOGGER = getLogger(__name__)

# The logic of each skill is contained within its own class, which inherits
# base methods from the MycroftSkill class with the syntax you can see below:
# "class ____Skill(MycroftSkill)"


class AutomationHandlerSkill(MycroftSkill):

    # The constructor of the skill, which calls MycroftSkill's constructor
    def __init__(self):
        super(AutomationHandlerSkill, self).__init__(
            name="AutomationHandlerSkill")
        self.command = ""
        self.dictionnary = {'1' : 'open atom','2' : 'open firefox'}
        self.auto = False
        # self.automationhandler_path = expanduser('~/.config/automationhandler')

    # def _configure_automationhandler(self):
    #     """
    #         Initiates automationhandler configurations.
    #     """
    #     if self._is_setup:
    #         if not exists(self.automationhandler_path):
    #             makedirs(self.automationhandler_path)

    #         config_path = join(self.automationhandler_path, 'config')

    #         with open(config_path, 'w+') as f:
    #             config = 'name = {}\n' + \
    #                      'surname = {}'

    #             f.write(config.format(self.settings["name"], self.settings["surname"]))

    @intent_handler(IntentBuilder('DirectStartIntent')
                    .require("DirectStartKeyword"))
    @adds_context('AutomationChoiceContext')
    def handle_direct_start_intent(self, message):
        self.speak("For now I have detected that you have {} habits when using Mycroft."
                   "\n\nShould I list them for you?"
                   .format(len(self.dictionnary)),
                   expect_response=True)

    @intent_handler(IntentBuilder('AutomationChoiceIntent')
                    .require("YesKeyword")
                    .require('AutomationChoiceContext').build())
    @adds_context('TriggerChoiceContext')
    @removes_context('AutomationChoiceContext')
    def handle_automation_choice_intent(self, message):
        self.auto = True
        self.speak("The habits your are using are:"
                    "\n\n{}"
                    "\n\n{}"
                   .format(self.dictionnary.get('1'),self.dictionnary.get('2')),
                   expect_response=True)

    # The "stop" method defines what Mycroft does when told to stop during
    # the skill's execution. In this case, since the skill's functionality
    # is extremely simple, the method just contains the keyword "pass", which
    # does nothing.
    def stop(self):
        pass

# The "create_skill()" method is used to create an instance of the skill.
# Note that it's outside the class itself.


def create_skill():
    return AutomationHandlerSkill()
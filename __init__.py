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
from os.path import dirname

from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill
from mycroft.skills.core import intent_handler
from mycroft.skills.context import adds_context, removes_context
from mycroft.util.log import getLogger

__author__ = 'Nuttymoon'

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
        self.auto = False

    @intent_handler(IntentBuilder('FakeStartIntent').require("Command")
                    .require("FakeStartKeyword"))
    @adds_context('AutomationChoiceContext')
    def handle_fake_start_intent(self, message):
        self.command = message.data.get("Command")
        self.speak("I noticed that you often use the command {}, "
                   "the command {} and the command {} together. "
                   "Do you want me to automate your habit "
                   "of launching these 3 commands?"
                   .format(self.command, self.command, self.command),
                   expect_response=True)

    @intent_handler(IntentBuilder('AutomationChoiceIntent')
                    .require("YesKeyword")
                    .require('AutomationChoiceContext').build())
    @adds_context('TriggerChoiceContext')
    @removes_context('AutomationChoiceContext')
    def handle_automation_choice_intent(self, message):
        self.auto = True
        self.speak("The habit automation can be triggered either by "
                   "only one of the previous commands or by any of them. "
                   "Do you want to pick one "
                   "particular command as the trigger?",
                   expect_response=True)

    @intent_handler(IntentBuilder('NoAutomationIntent')
                    .require("NoKeyword")
                    .require('AutomationChoiceContext').build())
    @adds_context('OfferChoiceContext')
    @removes_context('AutomationChoiceContext')
    def handle_no_automation_intent(self, message):
        self.auto = False
        self.speak("Should I offer you to launch the entire habit when you "
                   "launch one of the previous commands?",
                   expect_response=True)

    @intent_handler(IntentBuilder('TriggerChoiceIntent')
                    .require("YesKeyword")
                    .require('TriggerChoiceContext').build())
    @adds_context('TriggerCommandContext')
    @removes_context('TriggerChoiceContext')
    def handle_trigger_choice_intent(self, message):
        self.ask_trigger_command()

    @intent_handler(IntentBuilder('NoTriggerChoiceIntent')
                    .require("NoKeyword")
                    .require('TriggerChoiceContext').build())
    @removes_context('TriggerChoiceContext')
    def handle_no_trigger_choice_intent(self, message):
        if self.auto:
            self.habit_automatized()
        else:
            self.habit_not_automatized()

    @intent_handler(IntentBuilder('OfferChoiceIntent')
                    .require("YesKeyword")
                    .require('OfferChoiceContext').build())
    @adds_context('TriggerCommandContext')
    @removes_context('OfferChoiceContext')
    def handle_offer_choice_intent(self, message):
        self.ask_trigger_command()

    @intent_handler(IntentBuilder('NoOfferChoiceIntent')
                    .require("NoKeyword")
                    .require('OfferChoiceContext').build())
    @removes_context('OfferChoiceContext')
    def handle_no_offer_choice_intent(self, message):
        self.habit_not_automatized()

    @intent_handler(IntentBuilder('TriggerCommandIntent')
                    .require("IndexKeyword")
                    .require('TriggerCommandContext').build())
    @removes_context('TriggerCommandContext')
    def handle_trigger_command_intent(self, message):
        if message.data.get("IndexKeyword") == "cancel":
            self.habit_not_automatized()
        else:
            if self.auto:
                self.habit_automatized()
            else:
                self.habit_offer()

    def ask_trigger_command(self):
        self.speak("The trigger can be 1, {}. 2, {}. 3, {}. "
                   "Please answer by 1, 2, 3 or cancel."
                   .format(self.command, self.command, self.command),
                   expect_response=True)

    def habit_automatized(self):
        self.speak("The habit has been successfully automatized. You can "
                   "change your habit automation preferences with the "
                   "command 'habit automation'.")

    def habit_not_automatized(self):
        self.speak("The habit will not be automatized. You can change your "
                   "habit automation preferences with the command "
                   "'habit automation'.")

    def habit_offer(self):
        self.speak("Every time you will launch the command {}, "
                   "I will ask you if you want to launch the habit. You can "
                   "change your habit automation preferences with the command "
                   "'habit automation'."
                   .format(self.command))

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

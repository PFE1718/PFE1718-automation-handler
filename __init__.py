# Copyright 2016 Mycroft AI, Inc.
#
# This file is part of Mycroft Core.
#
# Mycroft Core is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Mycroft Core is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Mycroft Core.  If not, see <http://www.gnu.org/licenses/>.


# Visit https://docs.mycroft.ai/skill.creation for more detailed information
# on the structure of this skill and its containing folder, as well as
# instructions for designing your own skill based on this template.


# Import statements: the list of outside modules you'll be using in your
# skills, whether from other files in mycroft-core or from external libraries
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

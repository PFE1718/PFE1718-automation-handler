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
import json

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


class HabitsManager():
    def __init__(self):
        self.habits_file_path = "/opt/mycroft/habits/habits.json"
        self.habits = json.load(open(self.habits_file_path))

    def get_all_habits(self):
        return self.habits

    def get_habit_by_id(self, habit_id):
        return self.habits[habit_id]

    def automate_habit(self, habit_id, triggers, auto):
        self.habits[habit_id]["user_choice"] = True
        self.habits[habit_id]["automatized"] = auto
        if self.habits[habit_id]["trigger_type"] == "time":
            self.habits[habit_id]["time"] = triggers
        else:
            self.habits[habit_id]["triggers"] = triggers
        with open(self.habits_file_path, 'w') as habits_file:
            json.dump(self.habits, habits_file)


class AutomationHandlerSkill(MycroftSkill):

    def __init__(self):
        super(AutomationHandlerSkill, self).__init__(
            name="AutomationHandlerSkill")
        self.command = ""
        self.habit = None
        self.habit_id = None
        self.auto = False
        self.manager = HabitsManager()

    def initialize(self):
        habit_detected = IntentBuilder("HabitDetectedIntent").require(
            "HabitDetectedKeyword").require("HabitNumber").build()
        self.register_intent(habit_detected,
                             self.handle_habit_detected)

    def handle_habit_detected(self, message):
        LOGGER.debug("Loading habit number " + message.data.get("HabitNumber"))
        self.set_context("AutomationChoiceContext")
        self.habit_id = message.data.get("HabitNumber")
        self.habit = self.manager.get_habit_by_id(self.habit_id)

        dialog = "I have noticed that you often use "
        if(self.habit["trigger_type"] == "skill"):
            dialog += self.generate_skill_trigger_dialog(self.habit["skills"])
        else:
            dialog += self.generate_time_trigger_dialog(
                self.habit["time"], self.habit["skills"])

        self.speak(dialog, expect_response=True)

    @intent_handler(IntentBuilder("AutomationChoiceIntent")
                    .require("YesKeyword")
                    .require("AutomationChoiceContext").build())
    @adds_context("TriggerChoiceContext")
    @removes_context("AutomationChoiceContext")
    def handle_automation_choice_intent(self, message):
        self.auto = True
        if self.habit["trigger_type"] == "skill":
            self.speak("The habit automation can be triggered either by "
                       "only one of the previous commands or by any of them. "
                       "Do you want to pick one "
                       "particular command as the trigger?",
                       expect_response=True)
        else:
            self.remove_context("TriggerChoiceContext")
            self.manager.automate_habit(self.habit_id, self.habit["time"], 1)
            self.habit_automatized()

    @intent_handler(IntentBuilder("NoAutomationIntent")
                    .require("NoKeyword")
                    .require("AutomationChoiceContext").build())
    @adds_context("OfferChoiceContext")
    @removes_context("AutomationChoiceContext")
    def handle_no_automation_intent(self, message):
        if self.habit["trigger_type"] == "time":
            dial = ("Should I offer you to launch the entire habit"
                    " at {}?").format(self.habit["time"])
        else:
            dial = ("Should I offer you to launch the entire habit when you "
                    "launch one of the previous commands?")
        self.speak(dial, expect_response=True)

    @intent_handler(IntentBuilder("TriggerChoiceIntent")
                    .require("YesKeyword")
                    .require("TriggerChoiceContext").build())
    @adds_context("TriggerCommandContext")
    @removes_context("TriggerChoiceContext")
    def handle_trigger_choice_intent(self, message):
        self.ask_trigger_command()

    @intent_handler(IntentBuilder("NoTriggerChoiceIntent")
                    .require("NoKeyword")
                    .require("TriggerChoiceContext").build())
    @removes_context("TriggerChoiceContext")
    def handle_no_trigger_choice_intent(self, message):
        if self.auto:
            self.manager.automate_habit(
                self.habit_id, range(0, len(self.habit["skills"])), 1)
            self.habit_automatized()
        else:
            self.habit_not_automatized()

    @intent_handler(IntentBuilder("OfferChoiceIntent")
                    .require("YesKeyword")
                    .require("OfferChoiceContext").build())
    @adds_context("TriggerCommandContext")
    @removes_context("OfferChoiceContext")
    def handle_offer_choice_intent(self, message):
        if self.habit["trigger_type"] == "skill":
            self.ask_trigger_command()
        else:
            self.remove_context("TriggerCommandContext")
            self.manager.automate_habit(self.habit_id, self.habit["time"], 2)
            self.habit_offer()

    @intent_handler(IntentBuilder("NoOfferChoiceIntent")
                    .require("NoKeyword")
                    .require("OfferChoiceContext").build())
    @removes_context("OfferChoiceContext")
    def handle_no_offer_choice_intent(self, message):
        self.habit_not_automatized()

    @intent_handler(IntentBuilder("TriggerCommandIntent")
                    .require("IndexKeyword")
                    .require("TriggerCommandContext").build())
    @removes_context("TriggerCommandContext")
    def handle_trigger_command_intent(self, message):
        skill_id = message.data.get("IndexKeyword")
        if skill_id == "cancel":
            self.habit_not_automatized()
        else:
            if self.auto:
                self.manager.automate_habit(
                    self.habit_id, [int(skill_id) - 1], 1)
                self.habit_automatized()
            else:
                self.manager.automate_habit(
                    self.habit_id, [int(skill_id) - 1], 2)
                self.habit_offer(int(skill_id))

    def generate_skill_trigger_dialog(self, skills):
        dial = ""
        for i in range(0, len(skills) - 1):
            dial += "the command {}, ".format(skills[i]["last_utterance"])
        dial += "and the command {} together. ".format(
            skills[len(skills) - 1]["last_utterance"])
        dial += ("Do you want me to automate your habit of launching these "
                 "{} commands?".format(len(skills)))
        return dial

    def generate_time_trigger_dialog(self, time, skills):
        dial = ""
        if len(skills) > 1:
            for i in range(0, len(skills) - 1):
                dial += "the command {}, ".format(skills[i]["last_utterance"])
            dial += "and the command {} together ".format(
                skills[len(skills) - 1]["last_utterance"])
            com = "these {} commands".format(len(skills))
        else:
            dial += "the command {} ".format(skills[0]["last_utterance"])
            com = "this command"
        at = "at {}".format(time)
        dial += ("Do you want me to automate your habit of launching {} "
                 "{}?".format(com, at))
        return dial

    def ask_trigger_command(self):
        dialog = "The habit trigger can be "
        num = ""
        for i in range(0, len(self.habit["skills"])):
            dialog += "{}, {}. ".format(i + 1, self.habit["skills"]
                                        [i]["last_utterance"])
            num += "{}, ".format(i + 1)
        dialog += "Please answer {}or cancel.".format(num)
        self.speak(dialog, expect_response=True)

    def habit_automatized(self):
        self.speak("The habit has been successfully automatized. You can "
                   "change your habit automation preferences with the "
                   "command 'habit automation'.")

    def habit_not_automatized(self):
        self.speak("The habit will not be automatized. You can change your "
                   "habit automation preferences with the command "
                   "'habit automation'.")

    def habit_offer(self, skill_id=None):
        if self.habit["trigger_type"] == "time":
            dial = "Every day at {}, ".format(self.habit["time"])
        else:
            dial = "Every time you will launch the command {}, ".format(
                self.habit["skills"][skill_id]["last_utterance"])
        dial += ("I will ask you if you want to launch the habit. You can "
                 "change your habit automation preferences with the command "
                 "'habit automation'.")
        self.speak(dial)

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

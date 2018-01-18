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

from os.path import dirname
import json

from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill
from mycroft.skills.core import intent_handler
from mycroft.skills.context import adds_context, removes_context
from mycroft.util.log import getLogger
from mycroft.messagebus.message import Message

__author__ = 'Nuttymoon'

# Logger: used for debug lines, like "LOGGER.debug(xyz)". These
# statements will show up in the command line when running Mycroft.
LOGGER = getLogger(__name__)


class HabitsManager(object):
    '''
    This class manages the reading and writting in the file habits.json

    Attributes:
        habits_file_path (str): path to the file habits.json
        habits (json): the json datastore corresponding to habits.json
    '''

    def __init__(self):
        self.habits_file_path = "/opt/mycroft/habits/habits.json"
        self.triggers_file_path = "/opt/mycroft/habits/triggers.json"
        self.habits = json.load(open(self.habits_file_path))
        self.triggers = json.load(open(self.triggers_file_path))

    def get_all_habits(self):
        '''Return all the existing habits of the user'''
        return self.habits

    def get_habit_by_id(self, habit_id):
        '''Return one particular habit of the user'''
        return self.habits[habit_id]

    def register_habit(self, trigger_type, intents, time=None):
        '''Register a new habit in habits.json'''
        if trigger_type == "skill":
            self.habits += [
                {
                    "intents": intents,
                    "trigger_type": trigger_type,
                    "automatized": 0,
                    "user_choice": False,
                    "triggers": []
                }
            ]
        else:
            self.habits += [
                {
                    "intents": intents,
                    "trigger_type": trigger_type,
                    "automatized": 0,
                    "user_choice": False,
                    "time": time
                }
            ]
        with open(self.habits_file_path, 'w') as habits_file:
            json.dump(self.habits, habits_file)

    def automate_habit(self, habit_id, triggers, auto):
        '''
        Register the automation of a habit in the habits.json

        Args:
            habit_id (str): the id of the habit to automate
            triggers (str[]): the intents tp register as triggers of the habit
            auto (int): 1 for full automation, 2 for habit offer when triggered
        '''
        self.habits[habit_id]["user_choice"] = True
        self.habits[habit_id]["automatized"] = auto
        if self.habits[habit_id]["trigger_type"] == "time":
            self.habits[habit_id]["time"] = triggers
        else:
            self.habits[habit_id]["triggers"] = triggers
        with open(self.habits_file_path, 'w') as habits_file:
            json.dump(self.habits, habits_file)

    def not_automate_habit(self, habit_id):
        '''
        Register the user choice of not automatizing a habit

        Args:
            habit_id (str): the id of the habit to not automate
        '''
        self.habits[habit_id]["user_choice"] = True
        self.habits[habit_id]["automatized"] = 0
        with open(self.habits_file_path, 'w') as habits_file:
            json.dump(self.habits, habits_file)

    def get_trigger_by_id(self, trigger_id):
        '''Return one particular habit trigger'''
        return self.triggers[trigger_id]


class AutomationHandlerSkill(MycroftSkill):
    '''
    This class implements the automation handler skill

    Attributes:
        habit (datastore): the current habit being handled
        habit_id (str): the id of the habit being handled
        trigger (datastore): the current trigger being handled
        to_execute (array): the intents to execute in the automation
        auto (bool): True if the user choose to automate the habit
        manager (HabitsManager): used to interact with habits.json
    '''

    def __init__(self):
        super(AutomationHandlerSkill, self).__init__(
            name="AutomationHandlerSkill")
        self.habit = None
        self.habit_id = None
        self.trigger = None
        self.to_execute = []
        self.auto = False
        self.manager = None

    def initialize(self):
        habit_detected = IntentBuilder("HabitDetectedIntent").require(
            "HabitDetectedKeyword").require("Number").build()
        self.register_intent(habit_detected, self.handle_habit_detected)

        trigger_detected = IntentBuilder("TriggerDetectedIntent").require(
            "TriggerDetectedKeyword").require("Number").build()
        self.register_intent(trigger_detected, self.handle_trigger_detected)

# region Mycroft first dialog

    def handle_habit_detected(self, message):
        LOGGER.debug("Loading habit number " + message.data.get("Number"))
        self.set_context("AutomationChoiceContext")
        self.manager = HabitsManager()
        self.habit_id = int(message.data.get("Number"))
        self.habit = self.manager.get_habit_by_id(self.habit_id)

        dialog = "I have noticed that you often use "
        if(self.habit["trigger_type"] == "skill"):
            dialog += self.generate_skill_trigger_dialog(self.habit["intents"])
        else:
            dialog += self.generate_time_trigger_dialog(
                self.habit["time"], self.habit["intents"])

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
                self.habit_id, range(0, len(self.habit["intents"])), 1)
            self.habit_automatized()
        else:
            self.manager.not_automate_habit(self.habit_id)
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
        self.manager.not_automate_habit(self.habit_id)
        self.habit_not_automatized()

    @intent_handler(IntentBuilder("TriggerCommandIntent")
                    .require("IndexKeyword")
                    .require("TriggerCommandContext").build())
    @removes_context("TriggerCommandContext")
    def handle_trigger_command_intent(self, message):
        skill_id = message.data.get("IndexKeyword")
        if skill_id == "cancel":
            self.manager.not_automate_habit(self.habit_id)
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

    def generate_skill_trigger_dialog(self, intents):
        dial = ""
        for i in range(0, len(intents) - 1):
            dial += "the command {}, ".format(intents[i]["last_utterance"])
        dial += "and the command {} together. ".format(
            intents[len(intents) - 1]["last_utterance"])
        dial += ("Do you want me to automate your habit of launching these "
                 "{} commands?".format(len(intents)))
        return dial

    def generate_time_trigger_dialog(self, time, intents):
        dial = ""
        if len(intents) > 1:
            for i in range(0, len(intents) - 1):
                dial += "the command {}, ".format(intents[i]["last_utterance"])
            dial += "and the command {} together ".format(
                intents[len(intents) - 1]["last_utterance"])
            com = "these {} commands".format(len(intents))
        else:
            dial += "the command {} ".format(intents[0]["last_utterance"])
            com = "this command"
        at = "at {}".format(time)
        dial += ("Do you want me to automate your habit of launching {} "
                 "{}?".format(com, at))
        return dial

    def ask_trigger_command(self):
        dialog = "The habit trigger can be "
        num = ""
        for i in range(0, len(self.habit["intents"])):
            dialog += "{}, {}. ".format(i + 1, self.habit["intents"]
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
                self.habit["intents"][skill_id]["last_utterance"])
        dial += ("I will ask you if you want to launch the habit. You can "
                 "change your habit automation preferences with the command "
                 "'habit automation'.")
        self.speak(dial)

# endregion

# region Habit Automation

    def handle_trigger_detected(self, message):
        self.manager = HabitsManager()
        LOGGER.debug("Loading trigger number " + message.data.get("Number"))
        self.trigger = self.manager.get_trigger_by_id(int(
            message.data.get("Number")))
        self.habit = self.manager.get_habit_by_id(
            int(self.trigger["habit_id"]))
        LOGGER.debug("Habit number " + self.trigger["habit_id"])

        if self.habit["automatized"] == 1:
            for intent in self.habit["intents"]:
                if intent["name"] != self.trigger["intent"] or \
                        intent["parameters"] != self.trigger["parameters"]:
                    self.to_execute.append(intent)
            self.exec_automation()
        elif self.habit["automatized"] == 2:
            self.set_context("OfferContext")
            self.offer_habit_exec()

    @intent_handler(IntentBuilder("CompleteAutomationIntent")
                    .require("YesKeyword")
                    .require("OfferContext").build())
    @removes_context("OfferContext")
    def handle_complete_automation(self, message):
        self.exec_automation()

    @intent_handler(IntentBuilder("NotCompleteAutomationIntent")
                    .require("NoKeyword")
                    .require("OfferContext").build())
    @removes_context("OfferContext")
    def handle_not_complete_automation(self, message):
        pass

    def offer_habit_exec(self):
        if self.habit["trigger_type"] == "skill":
            dialog = "Do you also want to run"
            n_commands = len(self.habit["intents"]) - 1
            for intent in self.habit["intents"]:
                if intent["name"] != self.trigger["intent"] or \
                        intent["parameters"] != self.trigger["parameters"]:
                    n_commands -= 1
                    if not n_commands:
                        dialog += " and"
                    dialog += " the command {}".format(
                        intent["last_utterance"])
                    self.to_execute.append(intent)
        else:
            pass

        self.speak(dialog + "?", expect_response=True)

    def exec_automation(self):
        LOGGER.debug("Launching habit...")
        for intent in self.to_execute:
            self.emitter.emit(
                Message("recognizer_loop:utterance",
                        {"utterances": [intent["last_utterance"]],
                         "lang": 'en-us'}))
        self.to_execute = []

# endregion

# region Habit registration test intent

    @intent_handler(IntentBuilder("RegisterHabitIntent")
                    .require("RegisterHabitKeyword"))
    def handle_register_habit(self, message):
        self.manager = HabitsManager()
        self.manager.register_habit("skill", [
            {
                "parameters": {
                    "Application": "atom"
                },
                "name": "-4359987462241748114:LaunchDesktopApplicationIntent",
                "last_utterance": "open atom"
            },
            {
                "parameters": {
                    "Application": "firefox"
                },
                "name": "-4359987462241748114:LaunchDesktopApplicationIntent",
                "last_utterance": "open firefox"
            }
        ])

# endregion

    def stop(self):
        pass


def create_skill():
    return AutomationHandlerSkill()

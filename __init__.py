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

import json
import os
import datetime
from dateutil import parser

from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill
from mycroft.skills.core import intent_handler
from mycroft.skills.context import adds_context, removes_context
from mycroft.util.log import getLogger
from mycroft.messagebus.message import Message
from mycroft.skills.settings import SkillSettings

__author__ = 'Nuttymoon'

# Logger: used for debug lines, like "LOGGER.debug(xyz)". These
# statements will show up in the command line when running Mycroft.
LOGGER = getLogger(__name__)

WEEKDAYS = [
    "mondays",
    "tuesdays",
    "wednesdays",
    "thursdays",
    "fridays",
    "saturdays",
    "sundays"
]

SKILLS_FOLDERS = {
    "/opt/mycroft/skills/PFE1718-skill-listener": "skill listener",
    "/opt/mycroft/skills/PFE1718-habit-miner": "habit miner",
    "/opt/mycroft/skills/PFE1718-automation-handler": "automation handler"
}


class HabitsManager(object):
    """
    This class manages the reading and writting in the file habits.json

    Attributes:
        habits_file_path (str): path to the file habits.json
        habits (json): the json datastore corresponding to habits.json
    """

    def __init__(self):
        self.habits_file_path = os.path.expanduser(
            "~/.mycroft/skills/ListenerSkill/habits/habits.json")
        self.triggers_file_path = os.path.expanduser(
            "~/.mycroft/skills/ListenerSkill/habits/triggers.json")

    def load_files(self):
        self.habits = json.load(open(self.habits_file_path))
        self.triggers = json.load(open(self.triggers_file_path))

    def get_all_habits(self):
        """Return all the existing habits of the user"""
        return self.habits

    def get_habit_by_id(self, habit_id):
        """Return one particular habit of the user"""
        return self.habits[habit_id]

    def register_habit(self, trigger_type, intents, time=None, days=None):
        """
        Register a new habit in habits.json

        Args:
            trigger_type (str): the habit trigger type ("time" or "skill")
            intents (datastore): the intents that are part of the habit
            time (str): the time of the habit (if time based)
            days (int[]): the days of the habit (if time based)
        """
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
                    "time": time,
                    "days": days
                }
            ]
        with open(self.habits_file_path, 'w') as habits_file:
            json.dump(self.habits, habits_file)

    def save_habits(self):
        with open(self.habits_file_path, 'w') as habits_file:
            json.dump(self.habits, habits_file)

    def automate_habit(self, habit_id, auto, new_triggers=None):
        """
        Register the automation of a habit in the habits.json

        Args:
            habit_id (int): the id of the habit to automate
            triggers (str[]): the intents to register as triggers of the habit
            auto (int): 1 for full automation, 2 for habit offer when triggered
        """
        habit = self.habits[habit_id]
        habit["user_choice"] = True
        habit["automatized"] = auto

        if habit["trigger_type"] == "skill":
            if not self.triggers:
                for i in new_triggers:
                    self.triggers += [
                        {
                            "intent": habit["intents"][i]["name"],
                            "parameters": habit["intents"][i]["parameters"],
                            "habit_id": habit_id
                        }
                    ]
            else:
                if not self.check_triggers(habit_id, habit, new_triggers):
                    return False

            habit["triggers"] = new_triggers
            with open(self.triggers_file_path, 'w') as triggers_file:
                json.dump(self.triggers, triggers_file)

        self.habits[habit_id] = habit
        with open(self.habits_file_path, 'w') as habits_file:
            json.dump(self.habits, habits_file)

        return True

    def check_triggers(self, habit_id, habit, new_triggers):
        """
        Check if any trigger of new_triggers is already a trigger of a habit

        Args:
            habit_id (int): the id of the habit to check
            habit (datastore): the habit to check
            new_triggers (datastore): the new triggers to check
        """
        to_add = []
        for known_trig in self.triggers:
            for i in new_triggers:
                LOGGER.info("Testing trigger" + str(habit["intents"][int(i)]))
                if habit["intents"][i]["name"] == known_trig["intent"] and \
                    habit["intents"][i]["parameters"] \
                        == known_trig["parameters"]:
                    return False
                to_add += [
                    {
                        "intent": habit["intents"][i]["name"],
                        "parameters": habit["intents"][i]["parameters"],
                        "habit_id": habit_id
                    }
                ]
        self.triggers += to_add

        return True

    def not_automate_habit(self, habit_id):
        """
        Register the user choice of not automatizing a habit

        Args:
            habit_id (int): the id of the habit to not automate
        """
        self.habits[habit_id]["user_choice"] = True
        self.habits[habit_id]["automatized"] = 0
        with open(self.habits_file_path, 'w') as habits_file:
            json.dump(self.habits, habits_file)

    def get_trigger_by_id(self, trigger_id):
        """Return one particular habit trigger"""
        return self.triggers[trigger_id]


class AutomationHandlerSkill(MycroftSkill):
    """
    This class implements the automation handler skill

    Attributes:
        habit (datastore): the current habit being handled
        habit_id (str): the id of the habit being handled
        trigger (datastore): the current trigger being handled
        to_execute (datastore): the intents to execute in the automation
        auto (bool): True if the user choose to automate the habit
        manager (HabitsManager): used to interact with habits.json
    """

    def __init__(self):
        super(AutomationHandlerSkill, self).__init__(
            name="AutomationHandlerSkill")
        self.habit = None
        self.habit_id = None
        self.trigger = None
        self.to_execute = []
        self.to_install = []
        self.auto = False
        self.manager = HabitsManager()
        self.first_automation = True

    def initialize(self):
        habit_detected = IntentBuilder("HabitDetectedIntent").require(
            "HabitDetectedKeyword").require("Number").build()
        self.register_intent(habit_detected, self.handle_habit_detected)

        trigger_detected = IntentBuilder("TriggerDetectedIntent").require(
            "TriggerDetectedKeyword").require("Number").build()
        self.register_intent(trigger_detected, self.handle_trigger_detected)

# region Mycroft first dialog

    def handle_habit_detected(self, message):
        if not self.check_skills_intallation():
            return

        LOGGER.info("Loading habit number " + message.data.get("Number"))
        LOGGER.info("multiple_triggers = " + str(
            self.settings.get("multiple_triggers")))
        self.manager.load_files()
        self.habit_id = int(message.data.get("Number"))
        self.habit = self.manager.get_habit_by_id(self.habit_id)

        if self.habit["user_choice"]:
            LOGGER.info("User choice already made for this habit")
            return

        self.set_context("AutomationChoiceContext")
        dialog = "I have noticed that you often use "
        if self.habit["trigger_type"] == "skill":
            dialog += self.generate_skill_trigger_dialog(self.habit["intents"])
        else:
            dialog += self.generate_time_trigger_dialog(
                self.habit["time"], self.habit["days"], self.habit["intents"])
            event_name = "habit_automation_nb_{}".format(self.habit_id)
            self.schedule_repeating_event(self.handle_scheduled_habit,
                                          parser.parse(self.habit["time"]),
                                          86400, {"habit_id": self.habit_id,
                                                  "event_name": event_name},
                                          event_name)

        self.speak(dialog, expect_response=True)

    @intent_handler(IntentBuilder("AutomationChoiceIntent")
                    .require("YesKeyword")
                    .require("AutomationChoiceContext").build())
    def handle_automation_choice_intent(self):
        self.auto = True
        self.remove_context("AutomationChoiceContext")
        if self.habit["trigger_type"] == "skill":
            if self.settings.get("multiple_triggers"):
                self.set_context("TriggerChoiceContext")
                self.speak("The habit automation can be triggered either by "
                           "only one of the previous commands or by any of "
                           "them. Do you want to pick one "
                           "particular command as the trigger?",
                           expect_response=True)
            else:
                self.set_context("TriggerCommandContext")
                self.ask_trigger_command()

        else:
            self.manager.automate_habit(self.habit_id, 1 if self.auto else 2)
            self.habit_automatized()

    @intent_handler(IntentBuilder("NoAutomationIntent")
                    .require("NoKeyword")
                    .require("AutomationChoiceContext").build())
    @adds_context("OfferChoiceContext")
    @removes_context("AutomationChoiceContext")
    def handle_no_automation_intent(self):
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
    def handle_trigger_choice_intent(self):
        self.ask_trigger_command()

    @intent_handler(IntentBuilder("NoTriggerChoiceIntent")
                    .require("NoKeyword")
                    .require("TriggerChoiceContext").build())
    def handle_no_trigger_choice_intent(self):
        self.remove_context("TriggerChoiceContext")
        if self.auto:
            if self.manager.automate_habit(
                    self.habit_id, 1,
                    range(0, len(self.habit["intents"]))):
                self.habit_automatized()
            else:
                self.set_context("TriggerCommandContext")
                self.speak("One of these command is already a trigger for "
                           "another habit. Please select one command.")
                self.ask_trigger_command()
        else:
            self.manager.not_automate_habit(self.habit_id)
            self.habit_not_automatized()

    @intent_handler(IntentBuilder("OfferChoiceIntent")
                    .require("YesKeyword")
                    .require("OfferChoiceContext").build())
    def handle_offer_choice_intent(self):
        self.remove_context("OfferChoiceContext")
        if self.habit["trigger_type"] == "skill":
            self.set_context("TriggerCommandContext")
            self.ask_trigger_command()
        else:
            self.manager.automate_habit(self.habit_id, 1 if self.auto else 2)
            self.habit_offer()

    @intent_handler(IntentBuilder("NoOfferChoiceIntent")
                    .require("NoKeyword")
                    .require("OfferChoiceContext").build())
    @removes_context("OfferChoiceContext")
    def handle_no_offer_choice_intent(self):
        self.manager.not_automate_habit(self.habit_id)
        self.habit_not_automatized()

    @intent_handler(IntentBuilder("TriggerCommandIntent")
                    .require("IndexKeyword")
                    .require("TriggerCommandContext").build())
    def handle_trigger_command_intent(self, message):
        intent_id = message.data.get("IndexKeyword")
        if intent_id == "cancel":
            self.remove_context("TriggerCommandContext")
            self.manager.not_automate_habit(self.habit_id)
            self.habit_not_automatized()
        else:
            intent_id = int(intent_id) - 1
            if self.manager.automate_habit(
                    self.habit_id, 1 if self.auto else 2, [intent_id]):
                self.remove_context("TriggerCommandContext")
                if self.auto:
                    self.habit_automatized()
                else:
                    self.habit_offer(intent_id)
            else:
                self.speak("This command is already a trigger for another "
                           "habit. Please choose an other one.")
                self.ask_trigger_command()

    def generate_skill_trigger_dialog(self, intents):
        dial = ""
        for i in range(0, len(intents) - 1):
            dial += "the command {}, ".format(intents[i]["last_utterance"])
        dial += "and the command {} together. ".format(
            intents[len(intents) - 1]["last_utterance"])
        dial += ("Do you want me to automate your habit of launching these "
                 "{} commands?".format(len(intents)))
        return dial

    def generate_time_trigger_dialog(self, time, days, intents):
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
        at = "at {} on ".format(time)
        for d in days[:-1]:
            at += "{}, ".format(WEEKDAYS[d])
        if len(days) > 1:
            at += "and "
        at += "{}".format(WEEKDAYS[days[-1]])
        dial += ("{}. Do you want me to automate your habit of launching {} "
                 "{}?".format(at, com, at))
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
        dial = "The habit has been successfully automatized."
        if self.first_automation:
            dial += (" You can change your preferences by saying "
                     "'list habits'")
            self.first_automation = False
        self.speak(dial)

    def habit_not_automatized(self):
        dial = "The habit will not be automatized."
        if self.first_automation:
            dial += (" You can change your preferences by saying "
                     "'list habits'")
            self.first_automation = False
        self.speak(dial)

    def habit_offer(self, intent_id=None):
        if self.habit["trigger_type"] == "time":
            dial = "Every day at {}, ".format(self.habit["time"])
        else:
            dial = "Every time you will launch the command {}, ".format(
                self.habit["intents"][intent_id]["last_utterance"])
        dial += ("I will ask you if you want to launch the habit.")
        if self.first_automation:
            dial += (" You can change your preferences by saying "
                     "'list habits'")
            self.first_automation = False
        self.speak(dial)

# endregion

# region Habit Automation

    def handle_trigger_detected(self, message):
        if not self.check_skills_intallation():
            return

        self.manager.load_files()
        LOGGER.info("Loading trigger number " + message.data.get("Number"))
        self.trigger = self.manager.get_trigger_by_id(int(
            message.data.get("Number")))
        self.habit = self.manager.get_habit_by_id(self.trigger["habit_id"])
        LOGGER.info("Habit number " + str(self.trigger["habit_id"]))

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
    def handle_complete_automation(self):
        self.exec_automation()

    @intent_handler(IntentBuilder("NotCompleteAutomationIntent")
                    .require("NoKeyword")
                    .require("OfferContext").build())
    @removes_context("OfferContext")
    def handle_not_complete_automation(self):
        self.to_execute = []

    def handle_scheduled_habit(self, message):
        self.manager.load_files()
        self.habit_id = message.data.get("habit_id")
        self.habit = self.manager.get_habit_by_id(self.habit_id)
        if self.habit["automatized"] and \
                datetime.datetime.today().weekday() in self.habit["days"]:
            if self.habit["automatized"] == 1:
                self.to_execute = self.habit["intents"]
                self.exec_automation()
            else:
                self.set_context("OfferContext")
                self.offer_habit_exec()

    def offer_habit_exec(self):
        if self.habit["trigger_type"] == "skill":
            dialog = "Do you also want to run"
            n_commands = len(self.habit["intents"]) - 1
            for intent in self.habit["intents"]:
                if intent["name"] != self.trigger["intent"] or \
                        intent["parameters"] != self.trigger["parameters"]:
                    n_commands -= 1
                    if not n_commands and len(self.habit["intents"]) != 2:
                        dialog += " and"
                    dialog += " the command {}".format(
                        intent["last_utterance"])
                    self.to_execute.append(intent)
        else:
            dialog = "It is {}. Do you want to run".format(self.habit["time"])
            self.to_execute = self.habit["intents"]
            n_commands = len(self.habit["intents"])
            for intent in self.habit["intents"]:
                n_commands -= 1
                if not n_commands and len(self.habit["intents"]) != 1:
                    dialog += " and"
                dialog += " the command {}".format(intent["last_utterance"])

        self.speak(dialog + "?", expect_response=True)

    def exec_automation(self):
        LOGGER.info("Launching habit...")
        for intent in self.to_execute:
            self.emitter.emit(
                Message("recognizer_loop:utterance",
                        {"utterances": [intent["last_utterance"]],
                         "lang": 'en-us'}))
        self.to_execute = []

    @intent_handler(IntentBuilder("CancelHabitIntent")
                    .require("CancelHabitKeyword")
                    .require("Number").build())
    def handle_cancel_habit(self, message):
        self.habit_id = message.data.get("Number")
        self.cancel_scheduled_event(
            "habit_automation_nb_{}".format(self.habit_id))

# endregion

# region Habit modification

    @intent_handler(IntentBuilder("ListHabitsIntent")
                    .require("ListHabitsKeyword"))
    @adds_context("ListContext")
    def handle_list_habits(self):
        self.habits_list = []
        self.list_index = -1
        self.manager.load_files()

        i = 0
        for habit in self.manager.habits:
            if habit["user_choice"]:
                self.habits_list += [(i, habit)]
            i += 1

        self.speak("Listing habits one by one. After each habit, "
                   "you can modify it by saying modify, move to the next habit"
                   " by saying next habit, or stop the listing by saying "
                   "exit.")

        self.speak_next_habit()

    @intent_handler(IntentBuilder("NextHabitIntent")
                    .require("NextHabitKeyword")
                    .require("ListContext").build())
    def handle_next_habit(self):
        self.speak_next_habit()

    @intent_handler(IntentBuilder("ModifyHabitIntent")
                    .require("ModifyKeyword")
                    .require("ListContext").build())
    @adds_context("ModifyContext")
    @removes_context("ListContext")
    def handle_modify_habit(self):
        self.speak("Modifying habit {}. Say 0 to not automate, 1 to automate "
                   "entirely and 2 to automate the offer.".format(
                       self.list_index))

    @intent_handler(IntentBuilder("ExitListIntent")
                    .require("ExitKeyword")
                    .require("ListContext").build())
    @removes_context("ListContext")
    def handle_exit_list(self):
        self.speak("Stopping habits' list.")

    @intent_handler(IntentBuilder("ModifChoiceIntent")
                    .require("IndexAutoKeyword")
                    .require("ModifyContext").build())
    @adds_context("ListContext")
    @removes_context("ModifyContext")
    def handle_modif_choice(self, message):
        auto = int(message.data.get("IndexAutoKeyword"))
        index, _ = self.habits_list[self.list_index]
        self.manager.habits[index]["automatized"] = auto
        self.manager.save_habits()

        self.speak("Modification saved.")
        self.speak_next_habit()

    def speak_next_habit(self):
        self.list_index += 1

        if self.list_index == len(self.habits_list):
            self.remove_context("ListContext")
            self.speak("Habits' list finished.")
            return

        commands = ""
        _, hab = self.habits_list[self.list_index]
        if len(hab["intents"]) > 1:
            for intent in hab["intents"][:-1]:
                commands += "{}, ".format(intent["last_utterance"])
            commands += "and {}".format(hab["intents"][-1]["last_utterance"])
        else:
            commands += hab["intents"][0]["last_utterance"]
        stat = "automatized"
        if not hab["automatized"]:
            stat = "not " + stat
        elif hab["automatized"] == 2:
            stat = "offer " + stat

        optional = ""
        if hab["trigger_type"] == "time":
            optional += "Time: {} on ".format(hab["time"])
            for day in hab["days"]:
                optional += WEEKDAYS[day]
        else:
            trig = hab["intents"][hab["triggers"][0]]["last_utterance"]
            optional += "Trigger: {}".format(trig)
        optional += "."

        dial = "Habit {}. Commands: {}. {} Status: {}.".format(
            self.list_index, commands, optional, stat)
        self.speak(dial)

# endregion

# region Dependent skills installation

    def check_skills_intallation(self):
        LOGGER.info("Checking for skills install...")
        ret = True
        self.to_install = []

        for folder, skill in SKILLS_FOLDERS.iteritems():
            if not os.path.isdir(folder):
                ret = False
                self.to_install += [skill]

        if not ret:
            self.set_context("InstallMissingContext")
            dial = ("To use the skill automation handler, you also have to "
                    "install the skill")
            num_skill = "this skill"
            skills_list = ""
            for skill in self.to_install[:-1]:
                skills_list += skill + ", "
            if len(self.to_install) > 1:
                num_skill = "these {} skills".format(len(self.to_install))
                skills_list += "and "
                dial += "s"
            skills_list += self.to_install[-1]
            self.speak(dial + " " + skills_list +
                       ". Should I install {} for you?".format(num_skill),
                       expect_response=True)
        return ret

    @intent_handler(IntentBuilder("InstallMissingIntent")
                    .require("YesKeyword")
                    .require("InstallMissingContext").build())
    @removes_context("InstallMissingContext")
    def handle_install_missing(self):
        for skill in self.to_install:
            LOGGER.info("Installing " + skill)
            self.emitter.emit(
                Message("recognizer_loop:utterance",
                        {"utterances": ["install " + skill],
                         "lang": 'en-us'}))

    @intent_handler(IntentBuilder("NotInstallMissingIntent")
                    .require("NoKeyword")
                    .require("InstallMissingContext").build())
    @removes_context("InstallMissingContext")
    def handle_not_install_missing(self):
        pass

# endregion

    def stop(self):
        pass


def create_skill():
    return AutomationHandlerSkill()

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

    def register_habit(self, trigger_type, intents, time=None, days=None,
                       interval_max=None):
        """
        Register a new habit in habits.json

        Args:
            trigger_type (str): the habit trigger type ("time" or "skill")
            intents (datastore): the intents that are part of the habit
            time (str): the time of the habit (if time based)
            days (int[]): the days of the habit (if time based)
        """
        detected = True
        if not len(intents) > 0:
            detected = False

        if trigger_type == "skill":
            self.habits += [
                {
                    "intents": intents,
                    "trigger_type": trigger_type,
                    "automatized": 0,
                    "user_choice": False,
                    "triggers": [],
                    "detected": detected
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
                    "days": days,
                    "detected": detected,
                    "interval_max": interval_max
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

# endregion

# region Dialogs

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
        self.generate_settingsmeta()
        dial = "The habit has been successfully automatized."
        if self.first_automation:
            dial += (" You can change your preferences by modifying the "
                     "file /opt/mycroft/habits/habits dot json.")
            self.first_automation = False
        self.speak(dial)

    def habit_not_automatized(self):
        self.generate_settingsmeta()
        dial = "The habit will not be automatized."
        if self.first_automation:
            dial += (" You can change your preferences by modifying the "
                     "file /opt/mycroft/habits/habits dot json.")
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
            dial += (" You can change your preferences by modifying the "
                     "file /opt/mycroft/habits/habits dot json.")
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

# region Habit config on home.mycroft.ai

    def generate_settingsmeta(self):
        skill_dir = os.path.dirname(__file__)
        settingsmeta_file = "settingsmeta.json"
        settings_file = "settings.json"
        settings_path = os.path.join(skill_dir, settings_file)
        settingsmeta_path = os.path.join(skill_dir, settingsmeta_file)

        settingsmeta = json.load(open(settingsmeta_path))
        set_sections = settingsmeta["skillMetadata"]["sections"]

        commands = "["
        for intent in self.habit["intents"][:-1]:
            commands += "'" + intent["last_utterance"] + "', "
        commands += "'" + self.habit["intents"][-1]["last_utterance"] + "']"
        if self.habit["trigger_type"] == "skill":
            set_sections += [
                {
                    "name": "Habit {} (skill trigger)".format(self.habit_id),
                    "fields": [
                        {
                            "type": "label",
                            "label": "Commands: {}".format(commands)
                        },
                        {
                            "name": "habit_{}_auto".format(self.habit_id),
                            "type": "number",
                            "label": "Auto",
                            "value": str(self.habit["automatized"])
                        },
                        {
                            "type": "label",
                            "label": "Triggers: {}".format(
                                str(self.habit["triggers"]))
                        }
                    ]
                }
            ]
            self.settings["habit_{}_triggers".format(self.habit_id)] = "0"
        else:
            set_sections += [
                {
                    "name": "Habit {} (time trigger)".format(self.habit_id),
                    "fields": [
                        {
                            "type": "label",
                            "label": "Commands: {}".format(commands)
                        },
                        {
                            "name": "habit_{}_auto".format(self.habit_id),
                            "type": "number",
                            "label": "Auto",
                            "value": str(self.habit["automatized"])
                        },
                        {
                            "name": "habit_{}_time".format(self.habit_id),
                            "type": "text",
                            "label": "Time",
                            "value": self.habit["time"]
                        },
                        {
                            "name": "habit_{}_days".format(self.habit_id),
                            "type": "text",
                            "label": "Days",
                            "value": str(self.habit["days"])
                        }
                    ]
                }
            ]
            self.settings["habit_{}_time"
                          .format(self.habit_id)] = self.habit["time"]
            self.settings["habit_{}_days"
                          .format(self.habit_id)] = str(self.habit["days"])

        self.settings["habit_{}_commands".format(self.habit_id)] = commands
        self.settings["habit_{}_auto"
                      .format(self.habit_id)] = str(self.habit["automatized"])

        settingsmeta["skillMetadata"]["sections"] = set_sections

        with open(settings_path, 'w') as set_file:
            json.dump(self.settings, set_file)

        with open(settingsmeta_path, 'w') as meta_file:
            json.dump(settingsmeta, meta_file)

        s = SkillSettings(settings_file, 'HabitsSettings')
        s.initialize_remote_settings()

    @intent_handler(IntentBuilder("NewEmptyHabitIntent")
                    .require("NewEmptyHabitKeyword"))
    @adds_context("EmptyHabitTypeContext")
    def handle_create_empty_habit(self, message):
        self.speak("Do you want to create a time or a skill based habit?",
                   expect_response=True)

    @intent_handler(IntentBuilder("NewEmptySkillHabitIntent")
                    .require("SkillKeyword")
                    .require("EmptyHabitTypeContext").build())
    @removes_context("EmptyHabitTypeContext")
    def handle_new_empty_skill_habit(self):
        skill_dir = os.path.dirname(__file__)
        settingsmeta_file = "settingsmeta.json"
        settings_file = "settings.json"
        settings_path = os.path.join(skill_dir, settings_file)
        settingsmeta_path = os.path.join(skill_dir, settingsmeta_file)

        self.manager.load_files()
        h_index = 0
        if len(self.manager.habits) is not None:
            h_index = len(self.manager.habits)

        settingsmeta = json.load(open(settingsmeta_path))
        set_sections = settingsmeta["skillMetadata"]["sections"]
        set_sections += [
            {
                "name": "Habit {} (skill trigger)".format(h_index),
                "fields": [
                    {
                        "type": "label",
                        "label": ("Creating skill triggered habits is not "
                                  "supported for now!")
                    }
                ]
            }
        ]

        self.settings["habit_{}_commands".format(h_index)] = "[]"
        self.settings["habit_{}_auto".format(h_index)] = "0"
        self.settings["habit_{}_triggers".format(h_index)] = "[0]"

        settingsmeta["skillMetadata"]["sections"] = set_sections

        with open(settings_path, 'w') as set_file:
            json.dump(self.settings, set_file)

        with open(settingsmeta_path, 'w') as meta_file:
            json.dump(settingsmeta, meta_file)

        s = SkillSettings(settings_file, 'HabitsSettings')
        s.initialize_remote_settings()

        self.manager.register_habit("skill", [])

    @intent_handler(IntentBuilder("NewEmptyTimeHabitIntent")
                    .require("TimeKeyword")
                    .require("EmptyHabitTypeContext").build())
    @removes_context("EmptyHabitTypeContext")
    def handle_create_empty_time_habit(self):
        skill_dir = os.path.dirname(__file__)
        settingsmeta_file = "settingsmeta.json"
        settings_file = "settings.json"
        settings_path = os.path.join(skill_dir, settings_file)
        settingsmeta_path = os.path.join(skill_dir, settingsmeta_file)

        self.manager.load_files()
        h_index = 0
        if len(self.manager.habits) is not None:
            h_index = len(self.manager.habits)

        settingsmeta = json.load(open(settingsmeta_path))
        set_sections = settingsmeta["skillMetadata"]["sections"]
        set_sections += [
            {
                "name": "Habit {} (time trigger)".format(h_index),
                "fields": [
                    {
                        "name": "habit_{}_commands".format(h_index),
                        "type": "text",
                        "label": "Commands",
                        "value": ""
                    },
                    {
                        "name": "habit_{}_auto".format(h_index),
                        "type": "number",
                        "label": "Auto",
                        "value": "0"
                    },
                    {
                        "name": "habit_{}_time".format(h_index),
                        "type": "text",
                        "label": "Time",
                        "value": ""
                    },
                    {
                        "name": "habit_{}_days".format(h_index),
                        "type": "text",
                        "label": "Days",
                        "value": "[]"
                    }
                ]
            }
        ]

        self.settings["habit_{}_commands".format(h_index)] = "[]"
        self.settings["habit_{}_auto".format(h_index)] = "0"
        self.settings["habit_{}_time".format(h_index)] = ""
        self.settings["habit_{}_days".format(h_index)] = "[]"

        settingsmeta["skillMetadata"]["sections"] = set_sections

        with open(settings_path, 'w') as set_file:
            json.dump(self.settings, set_file)

        with open(settingsmeta_path, 'w') as meta_file:
            json.dump(settingsmeta, meta_file)

        s = SkillSettings(settings_file, 'HabitsSettings')
        s.initialize_remote_settings()

        self.manager.register_habit("time", [], time="", days=[])

    @intent_handler(IntentBuilder("LoadHabitsSettingsIntent")
                    .require("LoadSettingsKeyword"))
    def handle_load_habits_settings(self):
        self.manager.load_files()

        i = 0
        for hab in self.manager.habits:
            habit_name = "habit_" + str(i) + "_"
            if str(habit_name + "auto") in self.settings:
                if hab["trigger_type"] == "time":
                    hab["days"] = json.loads(
                        self.settings[habit_name + "days"])
                    if self.settings[habit_name + "time"] != hab["time"] \
                            and self.settings[habit_name + "time"] != "":
                        hab["time"] = self.settings[habit_name + "time"]
                        self.cancel_scheduled_event(
                            "habit_automation_nb_{}".format(i))
                        event_name = "habit_automation_nb_{}".format(i)
                        self.schedule_repeating_event(
                            self.handle_scheduled_habit,
                            parser.parse(hab["time"]),
                            86400, {"habit_id": i,
                                    "event_name": event_name},
                            event_name)
                    hab["automatized"] = int(
                        self.settings[habit_name + "auto"])
                    if not hab["detected"]:
                        intents = []
                        for command in json.loads(
                                str(self.settings[habit_name + "commands"])
                                .replace("'", "\"")):
                            intents += [
                                {
                                    "last_utterance": command,
                                    "parameters": {},
                                    "name": ""
                                }
                            ]
                        hab["intents"] = intents

                else:
                    if hab["detected"]:
                        hab["automatized"] = self.settings[habit_name + "auto"]

            else:
                LOGGER.info("No settings for habit number {}".format(i))

            i += 1

        self.manager.save_habits()


# endregion

    def stop(self):
        pass


def create_skill():
    return AutomationHandlerSkill()

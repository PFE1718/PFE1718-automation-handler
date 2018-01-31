## automation handler

Automation of user habits on Mycroft.

## Description

The automation-handler skill is part of the [**habits automation system**](https://github.com/PFE1718/mycroft-habits-automation) that aims to detect the **user habits** when using [Mycroft](https://mycroft.ai/), and to offer automation of these identified habits. You can find a detailed definition of a **habit** on the [project page](https://github.com/PFE1718/mycroft-habits-automation).

This skill allows the user to automate some of his/her habits that Mycroft has detected and handles the automation.

The habit detection is done by two other complementary skills:
1. The [**skill-listener**](https://github.com/PFE1718/mycroft-skill-listener), that logs the user activity. It is also  responsible for launching the 2 other skills when needed.
2. The [**habit-miner**](https://github.com/PFE1718/mycroft-habit-miner-skill), that extracts the habits of the user from the logs.

## Example

This skill is not made to be called by the user directly. It is automatically raised by the [**skill-listener**](https://github.com/PFE1718/mycroft-skill-listener) when needed to offer the automation of habits or to launch an entire habit.

## Credits
Gauthier LEONARD
## automation handler
Automation of detected user habits on Mycroft

## Description 
The automation-handler skill is part of a project aiming to detect user habits and allow their automation.
This skill allows the user to automate some of his/her habits that Mycroft has detected and handles the automation.

The habit detection is done by two other complementary skills:
- The [skill-listener](https://github.com/PFE1718/mycroft-skill-listener), that logs the user actions locally
- The [habit-miner](https://github.com/PFE1718/mycroft-habit-miner-skill), that uses Data Mining to extract the habits from the logs

The automation-handler skill is not made to be called by the user, it is automatically raised by the skill-listener when needed to offer the automation of habits or execute an entire habit.

## Examples 

## Credits 
Gauthier LEONARD
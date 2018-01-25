# Shell script to run before being able to use the skill
if [ ! -d "/opt/mycroft/habits" ]; then
    sudo mkdir /opt/mycroft/habits
    touch /opt/mycroft/habits/logs.json
    echo '[]' > /opt/mycroft/habits/habits.json
    echo '[]' > /opt/mycroft/habits/triggers.json
    sudo chmod -R ugo+rw /opt/mycroft/habits
fi
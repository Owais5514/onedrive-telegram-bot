Implement the following features in the bot
1. AI search should respond short and accurate (right now it spits out a really long text). If files are directly found, send the file to user directly, if more than one file is found, show all the files in the buttons, if no file is found then no need to show anything.
2.. Add ability to the AI search to search thorugh pdfs and images and other redable documents using least system resources and ai tokens.
3. Add an admin command to shut down the bot from the bot chat menu. Also, when unlimited users are added, push commits to the github repository to update it. Right now it doenst do that when it runs from github actions
4. add /about and /privacy commands to the bot for users who want to know more about this bot
5. Modify the /start command to display status information even if the scipt is not active
6. Add an admin function to mass send message to the sunscribed users
7. For users who are in the free tier, provide them with information to contact admin to activate more ai search queries
8. When the bot starts or shuts down, send messages to subscribed users with the bot started and bot ended message which will self destruct within 1 minute
9. any user commands should self destruct the moment the user sends it to keep the chat clean. This shold also delete all previous start command and ai search command messages (not sent files) when a user starts the bot newly
10. Bot should use least system resources to run so that the user experince is snappy. You can pre load the folder structure the bot can use when dispaying the contents of a folder to put less strain on the cpu
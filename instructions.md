# A Pythn Telegram Bot
The main of this script is to collect files and folders from github account (of owais ahmed) using the provided credentials in the .env file. 
- When a user gives the /start command, it will great the user and show buttons displaying, browse files and refresh (side by side). The names are self explanatory for their functions
- Pressing Browse files, the bot will display the files and folders that are inside the University Folder (the buttons will be dynamic, meaning its content will keep on changing based on user interaction, without needing to send new message every time)
- Pressing a folder will display the files and folders inside that folder. Pressing a file will promt the user if they want to download it. Once confirmed, it will send the file to the user directly to the chat.
- There will be total five commands, /start, /help, /admin (for admin user only), /privacy and /about . All of the commands are self explanatory and add necessary funcitons to it.
- Make the browsing of the files and folder faster by implementing a local index of the folder tree when the bot stats.
- For subscribed users, they will receive a message (that will delete within 1 minute of sending) saying "Bot Started Operations" and "Bot Ended Operations" whenever the bot is started and stopped by the admin.
- /admin function will have a bot shutdown command to get out of the bot polling loop and end the python script
- Make the code efficient and less systemm intensive by writing it in as few lines as possible
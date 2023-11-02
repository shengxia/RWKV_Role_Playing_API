class RoleInfo:

    def __init__(self, chatbot, user, bot, greeting, bot_persona, example_message, use_qa, log_hash):
        self.chatbot = chatbot
        self.user_chat = user
        self.bot_chat = bot
        self.user = user if not use_qa else 'User'
        self.bot = bot if not use_qa else 'Assistant'
        self.greeting = greeting
        self.bot_persona = bot_persona
        self.example_message = example_message
        self.log_hash = log_hash

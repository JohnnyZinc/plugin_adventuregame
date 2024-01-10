# encoding:utf-8

import plugins
from bridge.bridge import Bridge
from bridge.context import ContextType
from bridge.reply import Reply, ReplyType
from common import const
from common.expired_dict import ExpiredDict
from common.log import logger
from config import conf
from plugins import *


# https://github.com/bupticybee/ChineseAiTextBasedAdventureGameChatGPT
# 自定义故事逻辑
class TextBasedAdventureGame:
    def __init__(self, bot, sessionid, story):
        self.bot = bot
        self.sessionid = sessionid
        bot.sessions.clear_session(sessionid)
        self.first_interact = True
        self.story = story

    def reset(self):
        self.bot.sessions.clear_session(self.sessionid)
        self.first_interact = True

    def action(self, user_action):
        if user_action[-1] != "。":
            user_action = user_action + "。"
        if self.first_interact:
            prompt = (
                """我想让你扮演一个基于文本的冒险游戏。我在这个基于文本的冒险游戏中扮演一个角色。请尽可能具体地描述角色所看到的内容和环境。我将输入命令来告诉角色该做什么，而你需要回复角色的行动结果以推动游戏的进行。不要提供行动选项。
            开头是，"""
                + self.story
                + " "
                + user_action
            )
            self.first_interact = False
        else:
            prompt = """继续，一次只需要续写四到六句话，总共就只讲5分钟内发生的事情。""" + user_action
        return prompt


@plugins.register(
    name="TextBasedAdventureGame",
    desire_priority=0,
    namecn="文字冒险游戏",
    desc="A plugin to play text based adventure game",
    version="1.0",
    author="lanvent",
)
# 自定义上下文处理逻辑
class TextBasedAdventureGame(Plugin):
    def __init__(self):
        super().__init__()
        self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context
        logger.info("[TextBasedAdventureGame] inited")
        # 目前没有设计session过期事件，这里先暂时使用过期字典
        if conf().get("expires_in_seconds"):
            self.games = ExpiredDict(conf().get("expires_in_seconds"))
        else:
            self.games = dict()

    def on_handle_context(self, e_context: EventContext):
        if e_context["context"].type != ContextType.TEXT:
            return
        bottype = Bridge().get_bot_type("chat")
        if bottype not in [const.OPEN_AI, const.CHATGPT, const.CHATGPTONAZURE, const.LINKAI]:
            return
        bot = Bridge().get_bot("chat")
        content = e_context["context"].content[:]
        clist = e_context["context"].content.split(maxsplit=1)
        sessionid = e_context["context"]["session_id"]
        logger.debug("[TextBasedAdventureGame] on_handle_context. content: %s" % clist)
        trigger_prefix = conf().get("plugin_trigger_prefix", "$")
        if clist[0] == f"{trigger_prefix}停止冒险":
            if sessionid in self.games:
                self.games[sessionid].reset()
                del self.games[sessionid]
                reply = Reply(ReplyType.INFO, "冒险结束!")
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS
        elif clist[0] == f"{trigger_prefix}开始冒险" or sessionid in self.games:
            if sessionid not in self.games or clist[0] == f"{trigger_prefix}开始冒险":
                if len(clist) > 1:
                    story = clist[1]
                else:
                    prompt = """提供一个故事背景，只介绍世界观，字数保持在100字以内。主人公从某个地方醒来。主人公是我。"""
                    story = prompt
                self.games[sessionid] = TextBasedAdventureGame(bot, sessionid, story)
                reply = Reply(ReplyType.INFO, "冒险开始：" + story)
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS  # 事件结束，并跳过处理context的默认逻辑
            else:
                prompt = self.games[sessionid].action(content)
                e_context["context"].type = ContextType.TEXT
                e_context["context"].content = prompt
                e_context.action = EventAction.BREAK  # 事件结束，不跳过处理context的默认逻辑

    # 自定义帮助文本
    def get_help_text(self, **kwargs):
        help_text = "可以和机器人一起玩文字冒险游戏。\n"
        if kwargs.get("verbose") != True:
            return help_text
        trigger_prefix = conf().get("plugin_trigger_prefix", "$")
        help_text = f"{trigger_prefix}开始冒险 " + "背景故事: 开始一个基于{背景故事}的文字冒险，之后你的所有消息会协助完善这个故事。\n" + f"{trigger_prefix}停止冒险: 结束游戏。\n"
        if kwargs.get("verbose") == True:
            help_text += f"\n命令例子: '{trigger_prefix}开始冒险 你在树林里冒险，指不定会从哪里蹦出来一些奇怪的东西，你握紧手上的手枪，希望这次冒险能够找到一些值钱的东西，你往树林深处走去。'"
        return help_text
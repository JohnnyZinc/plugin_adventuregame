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


# https://github.com/bupticybee/ChineseAiDungeonChatGPT

class StoryTeller:
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
                """我想让你扮演一个基于文本的冒险游戏。我在这个基于文本的冒险游戏中扮演一个角色。请尽可能具体地描述角色所看到的内容和环境。我将输入命令来告诉角色该做什么，而你需要回复角色的行动结果以推动游戏的进行。不需要提供行动选项。
            开头是，"""
                + self.story
                + " "
                + user_action
            )
            self.first_interact = False
        else:
            prompt = user_action
        return prompt


@plugins.register(
    name="TextGame",
    desire_priority=0,
    namecn="文字游戏",
    desc="A plugin to play text game",
    version="1.0",
    author="johnny",
)

class TextGame(Plugin):
    def __init__(self):
        super().__init__()
        self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context
        logger.info("[TextGame] inited")
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
        logger.debug("[TextGame] on_handle_context. content: %s" % clist)
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
                    story = "当你醒来时，发现自己身处一个古老的城堡内。昏黄的灯光在石墙上投下阴影，墙壁上挂着古老的油画。一股潮湿的气息弥漫在空气中，让你感到一阵不安。你站在一个石头铺成的走廊中央，两边是黑暗的门廊。远处传来微弱的声音，仿佛有隐约的低语。地板下是一个石质的螺旋楼梯，通向未知的楼上。你的周围没有其他人，只有寂静和古老的氛围。你能听到墙角传来的微弱声音，似乎是某种生物的悉悉索索声。你也能感受到一种奇怪的能量，使你的皮肤微微发麻。在这神秘的城堡中，你能做的事情有很多。请告诉我你想要做什么，或者询问我关于周围环境的更多信息。"
                self.games[sessionid] = StoryTeller(bot, sessionid, story)
                reply = Reply(ReplyType.INFO, "冒险开始：" + story)
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS  # 事件结束，并跳过处理context的默认逻辑
            else:
                prompt = self.games[sessionid].action(content)
                e_context["context"].type = ContextType.TEXT
                e_context["context"].content = prompt
                e_context.action = EventAction.BREAK  # 事件结束，不跳过处理context的默认逻辑

    def get_help_text(self, **kwargs):
        help_text = "可以和机器人一起玩文字冒险游戏。\n"
        if kwargs.get("verbose") != True:
            return help_text
        trigger_prefix = conf().get("plugin_trigger_prefix", "$")
        help_text = f"{trigger_prefix}开始冒险 " + "背景故事: 开始一个基于{背景故事}的文字冒险，之后你的所有消息会协助完善这个故事。\n" + f"{trigger_prefix}停止冒险: 结束游戏。\n"
        if kwargs.get("verbose") == True:
            help_text += f"\n命令例子: '{trigger_prefix}开始冒险 你在树林里冒险，指不定会从哪里蹦出来一些奇怪的东西，你握紧手上的手枪，希望这次冒险能够找到一些值钱的东西，你往树林深处走去。'"
        return help_text

"""Iron Man style replies for admin actions and greetings.

Each action has several lines; one is picked at random every time.
Placeholders: {user} (HTML mention), {time}, {count}. The welcome and
goodbye lines use the normal welcome placeholders ({mention}, {first},
{chatname}...) and Markdown, like custom welcome messages.
"""
import random

LINES = {
    "ban": [
        "🔴 Repulsor blast fired! {user} ko group se bahar uda diya. Jarvis, darwaza lock karo. 🚪",
        "I am Iron Man… aur {user}, tum ab is group ka hissa nahi ho. 💥",
        "Suit up! {user} ko ban kar diya gaya. Agli baar rules padh lena. 📜",
        "Jarvis, target locked 🎯 … {user} banned. Mission complete.",
        "{user} ne galat Avenger se panga le liya. Ban hammer dropped! 🔨",
        "Arc reactor full power ⚡ {user} gaya, bye bye!",
        "Thanos ne snap kiya tha, maine ban kar diya. {user}, alvida 👋",
        "Stark Industries security alert 🚨 {user} permanently banned.",
    ],
    "tban": [
        "⏳ {user} ko {time} ke liye suit se bahar nikaal diya. Time out!",
        "Jarvis, {user} ka access {time} ke liye band karo. 🔒",
        "{user}, {time} ka break lo aur socho kya galti ki. 🧘",
        "Temporary repulsor blast! {user} banned for {time}. ⚡",
    ],
    "kick": [
        "🦾 Ek punch aur {user} group se bahar! Wapas aana hai toh tameez se aana.",
        "{user} ko Iron Man ne kick maara 👢 … darwaza khula hai, soch ke aana.",
        "Jarvis, {user} ko eject karo. 🚀 Ejected!",
        "Pew pew! 💥 {user} kicked. Rejoin karne se pehle rules padh lena.",
        "{user} ko Stark Tower se bahar fenk diya 🏙️",
    ],
    "unban": [
        "✅ Jarvis ne {user} ka ban hata diya. Welcome back, but behave! 😎",
        "{user}, doosra mauka mil raha hai. Iron Man sabko ek chance deta hai. 🤝",
        "Ban lifted! {user} ab wapas aa sakte hain. 🚪",
        "Arc reactor recharged ⚡ {user} unbanned.",
    ],
    "mute": [
        "🤐 Jarvis, {user} ka mic off karo. Muted!",
        "{user}, thoda shaant raho. Iron Man ne mute button daba diya. 🔇",
        "Silence mode activated 🔕 {user} ab bol nahi payenge.",
        "Bahut bol liye {user}, ab thoda sun bhi lo. 🤫 Muted.",
        "Suit ka volume zero 🔇 {user} muted.",
    ],
    "tmute": [
        "🔇 {user} ko {time} ke liye mute kiya. Chai pi ke aao ☕",
        "Jarvis, {user} ka mic {time} ke liye off. ⏳",
        "{user}, {time} ka silent mode on. 🤫",
    ],
    "unmute": [
        "🔊 {user} ka mic wapas on! Ab sambhal ke bolna.",
        "Jarvis, {user} ko awaaz wapas do. Unmuted! 🎤",
        "{user}, bolne ki azaadi wapas mil gayi. Use wisely 😎",
        "Silence mode off 🔊 {user} unmuted.",
    ],
    "approve": [
        "✅ {user} ab Stark Industries ka trusted member hai! Locks, blacklist aur antiflood ab inpe lagu nahi honge. 🦾",
        "Jarvis, {user} ko VIP list mein daalo. Approved! 🌟",
        "{user} ko Iron Man ka blessing mil gaya. Approved ✅",
        "Welcome to the Avengers, {user}! Tum approved ho. 💪",
    ],
    "unapprove": [
        "❌ {user} ab VIP list se bahar hain. Saare rules wapas lagu.",
        "Jarvis, {user} ka special access cancel karo. Unapproved.",
        "{user}, approval wapas le liya gaya. Ab behave karna. 👀",
    ],
    "warn": [
        "⚠️ {user}, yeh warning hai! Jarvis gin raha hai: {count}.",
        "Oye {user}! Sambhal ja, warning {count} ho gayi. ⚠️",
        "Iron Man dekh raha hai 👀 {user}, warning {count}.",
        "Repulsor charge ho raha hai ⚡ {user}, warning {count}. Agli baar seedha action!",
    ],
    "warn_ban": [
        "🔨 {user} ne saari warnings khatam kar di. Ban! Jarvis, file close karo.",
        "Warnings full, patience zero. {user} banned 💥",
    ],
    "warn_kick": [
        "👢 {user} ki warnings full! Group se bahar.",
        "Limit cross! {user} ko eject kiya. 🚀",
    ],
    "promote": [
        "🦾 {user} ko Iron Man suit mil gaya! Ab tum admin ho, power ka sahi use karna.",
        "Jarvis, {user} ko Avengers team mein add karo. Promoted! 🌟",
        "With great power comes great responsibility… {user}, ab tum admin ho! 💪",
    ],
    "demote": [
        "🔻 {user} ka suit wapas le liya gaya. Ab normal member ho.",
        "Jarvis, {user} ke admin powers revoke karo. Demoted.",
        "{user}, suit maintenance mein gaya hai. Admin rights hata diye. 🔧",
    ],
    "bot_joined": [
        "🦾 I am Iron Man! Add karne ke liye thanks. Mujhe admin bana do, phir dekho kamaal. /help",
        "Jarvis online ✅ Iron Man aa gaya! Admin rights do aur group ki security meri zimmedari.",
        "Suit up! 🦾 Iron Man reporting for duty. Admin bana do aur /help dekho.",
    ],
}

WELCOME_LINES = [
    "🦾 Arre {mention}! Welcome to *{chatname}*. Jarvis ne tumhara suit ready kar diya hai, maze karo! 🔥",
    "Jarvis, red carpet bichhao! 🎉 {mention} aa gaye hain *{chatname}* mein!",
    "I am Iron Man… aur tum ho {mention}! Welcome to the squad 💥",
    "Suit up, {mention}! 🦾 *{chatname}* mein swagat hai, rules padh lena aur masti karna 😎",
    "Arc reactor ka power badh gaya ⚡ kyunki {mention} aa gaye! Welcome!",
    "Avengers, assemble! 🛡️ Naya member {mention} join hua hai *{chatname}* mein.",
    "Stark Tower mein swagat hai {mention}! 🏙️ Chai, coffee ya shawarma? 🌯",
    "Ohooo {mention} aaye hain! 🎊 Jarvis, party mode on karo! 🎶",
    "Welcome {mention}! 🔥 Yahan sab family hain, bas limit cross mat karna 😉",
    "Jarvis scan complete ✅ {mention} officially awesome hai. Welcome to *{chatname}*!",
]

GOODBYE_LINES = [
    "👋 {first} chala gaya… Jarvis, seat khaali rakhna, shayad wapas aaye.",
    "{first} ne suit utaar diya aur chala gaya. Alvida dost! 🦾",
    "Ek Avenger kam ho gaya 😢 Bye {first}!",
    "{first} left the chat. Jarvis, mission log update karo. 📝",
    "Tata bye bye {first} 👋 Shawarma party tumhare bina hi hogi 🌯",
    "{first} gaya… lekin yaadein yahin rahengi. 💔",
]


def pick(kind, **values):
    """A random line for an action, with the placeholders filled in."""
    return random.choice(LINES[kind]).format(**values)

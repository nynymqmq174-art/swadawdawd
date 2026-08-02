import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import os

# ========== الإعدادات ==========
TOKEN = os.environ['TOKEN']
ALLOWED_ROLE_ID = 1532397766146265368
GUILD_ID = 1493906232921165894
APPLICATION_CHANNEL_ID = 1533604310401945610
APPROVE_ROLE_ID = 1532402417042194542
SUPPORT_VOICE_CHANNEL = 1532445572588372038
SUPPORT_NOTIFY_CHANNEL = 1533609279884361809

# ========== البوت ==========
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ==================== إشعار دخول الروم الصوتي ====================
@bot.event
async def on_voice_state_update(member, before, after):
    if after.channel and after.channel.id == SUPPORT_VOICE_CHANNEL:
        if before.channel is None or before.channel.id != SUPPORT_VOICE_CHANNEL:
            notify_channel = bot.get_channel(SUPPORT_NOTIFY_CHANNEL)
            if notify_channel:
                embed = discord.Embed(
                    title="🔔 إشعار دعم فني",
                    description=f"**يوجد شخص في انتظار الدعم**\n\n{member.mention} دخل الروم وينتظر مساعدة.",
                    color=0xFFA500,
                    timestamp=discord.utils.utcnow()
                )
                embed.set_thumbnail(url=member.display_avatar.url)
                embed.set_footer(text="SP8 System | انتظار الدعم")
                await notify_channel.send(embed=embed)

# ==================== البروتكاست ====================
class BroadcastModal(discord.ui.Modal, title="إرسال بروتكاست"):
    message = discord.ui.TextInput(
        label="اكتب رسالة البروتكاست",
        placeholder="اكتب الرسالة اللي تبي ترسلها لكل الأعضاء...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=2000
    )

    async def on_submit(self, interaction: discord.Interaction):
        if ALLOWED_ROLE_ID not in [role.id for role in interaction.user.roles]:
            await interaction.response.send_message("❌ ما عندك صلاحية.", ephemeral=True)
            return

        await interaction.response.send_message("⏳ جاري إرسال الرسائل...", ephemeral=True)
        sent = 0
        failed = 0

        for member in interaction.guild.members:
            if member.bot:
                continue
            try:
                await member.send(self.message.value)
                sent += 1
                await asyncio.sleep(1.2)
            except discord.Forbidden:
                failed += 1
            except Exception:
                failed += 1

        await interaction.followup.send(
            f"✅ **تم الانتهاء!**\n📤 نجح: `{sent}`\n❌ فشل: `{failed}`",
            ephemeral=True
        )

# ==================== أزرار القبول والرفض ====================
class ApplicationActionView(discord.ui.View):
    def __init__(self, applicant_id: int):
        super().__init__(timeout=None)
        self.applicant_id = applicant_id

    @discord.ui.button(label="✅ قبول", style=discord.ButtonStyle.success, custom_id="approve_app")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        if ALLOWED_ROLE_ID not in [role.id for role in interaction.user.roles]:
            await interaction.response.send_message("❌ ما عندك صلاحية.", ephemeral=True)
            return

        guild = interaction.guild
        member = guild.get_member(self.applicant_id)
        role = guild.get_role(APPROVE_ROLE_ID)

        if not member:
            await interaction.response.send_message("❌ العضو غير موجود.", ephemeral=True)
            return
        if not role:
            await interaction.response.send_message("❌ الرتبة غير موجودة.", ephemeral=True)
            return

        bot_member = guild.get_member(bot.user.id)
        if bot_member.top_role.position <= role.position:
            await interaction.response.send_message(
                "❌ البوت ما يقدر يعطي هالرتبة. خلي رتبة البوت أعلى من رتبة القبول.",
                ephemeral=True
            )
            return

        errors = []

        try:
            await member.add_roles(role, reason=f"تم القبول بواسطة {interaction.user}")
        except discord.Forbidden:
            errors.append("ما قدرت أعطي الرتبة")
        except Exception as e:
            errors.append(f"خطأ في الرتبة: {e}")

        try:
            await member.send(
                "🎉 **تهانينا! تم قبول تقديمك في سيرفر SP8.**\n\n"
                f"✅ تم منحك الرتبة: {role.mention}\n"
                "نتمنى لك التوفيق في مهامك الإدارية!"
            )
        except discord.Forbidden:
            errors.append("العضو قافل الخاص")
        except Exception as e:
            errors.append(f"خطأ في الإرسال: {e}")

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        status = f"✅ تم القبول بواسطة {interaction.user.mention}"
        if errors:
            status += f"\n⚠️ ملاحظات: {', '.join(errors)}"
        embed.add_field(name="📌 الحالة", value=status, inline=False)
        
        await interaction.message.edit(embed=embed, view=None)
        await interaction.response.send_message("✅ تم قبول المتقدم" + (" (مع ملاحظات)" if errors else ""), ephemeral=True)

    @discord.ui.button(label="❌ رفض", style=discord.ButtonStyle.danger, custom_id="reject_app")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        if ALLOWED_ROLE_ID not in [role.id for role in interaction.user.roles]:
            await interaction.response.send_message("❌ ما عندك صلاحية.", ephemeral=True)
            return

        guild = interaction.guild
        member = guild.get_member(self.applicant_id)
        errors = []

        if member:
            try:
                await member.send(
                    "❌ **نأسف لإبلاغك...**\n\n"
                    "تم رفض تقديمك في سيرفر **SP8**.\n"
                    "نتمنى لك التوفيق في مسارات أخرى."
                )
            except discord.Forbidden:
                errors.append("العضو قافل الخاص")
            except Exception as e:
                errors.append(f"خطأ: {e}")

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.red()
        status = f"❌ تم الرفض بواسطة {interaction.user.mention}"
        if errors:
            status += f"\n⚠️ ملاحظات: {', '.join(errors)}"
        embed.add_field(name="📌 الحالة", value=status, inline=False)
        
        await interaction.message.edit(embed=embed, view=None)
        await interaction.response.send_message("❌ تم رفض المتقدم" + (" (مع ملاحظات)" if errors else ""), ephemeral=True)

# ==================== نموذج التقديم ====================
class ApplyModal(discord.ui.Modal, title="نموذج التقديم"):
    name = discord.ui.TextInput(
        label="اسمك",
        placeholder="اكتب اسمك الكامل...",
        required=True,
        max_length=100
    )
    
    age = discord.ui.TextInput(
        label="عمرك",
        placeholder="مثال: 17",
        required=True,
        max_length=10
    )
    
    experience = discord.ui.TextInput(
        label="خبراتك الإدارية",
        placeholder="اشرح خبراتك بالتفصيل...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1000
    )
    
    previous_admin = discord.ui.TextInput(
        label="هل كنت إداري بسيرفر قبل؟",
        placeholder="نعم / لا - واذكر التفاصيل...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=500
    )

    async def on_submit(self, interaction: discord.Interaction):
        channel = bot.get_channel(APPLICATION_CHANNEL_ID)
        
        if not channel:
            await interaction.response.send_message("❌ روم التقديمات غير موجود.", ephemeral=True)
            return

        embed = discord.Embed(
            title="📝 تقديم جديد | SP8",
            description=(
                "إدارة سيرفر **SP8** تعلن عن فتح باب القبول والتقديم على الإدارة "
                "لمن لديه رغبة بالإلتحاق بعالم الإدارة نرجو تعبئة استمارة التقديم"
            ),
            color=0x5865F2,
            timestamp=interaction.created_at
        )
        embed.add_field(name="👤 الاسم", value=self.name.value, inline=True)
        embed.add_field(name="🎂 العمر", value=self.age.value, inline=True)
        embed.add_field(name="📋 الخبرات الإدارية", value=self.experience.value, inline=False)
        embed.add_field(name="🏛️ التجربة السابقة", value=self.previous_admin.value, inline=False)
        embed.add_field(name="🆔 المتقدم", value=interaction.user.mention, inline=False)
        embed.set_author(name=interaction.user.name, icon_url=interaction.user.display_avatar.url)
        embed.set_footer(text="SP8 System | تقديمات الإدارة")
        embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)

        view = ApplicationActionView(interaction.user.id)
        await channel.send(embed=embed, view=view)
        
        await interaction.response.send_message(
            "✅ تم إرسال تقديمك بنجاح! سيتم مراجعته من قبل الإدارة.",
            ephemeral=True
        )

class ApplyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="تقديم", emoji="📝", style=discord.ButtonStyle.primary, custom_id="apply_button")
    async def apply_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = ApplyModal()
        await interaction.response.send_modal(modal)

# ==================== الأوامر ====================
@bot.event
async def on_ready():
    print(f"✅ البوت شغال: {bot.user}")
    try:
        guild = discord.Object(id=GUILD_ID)
        bot.tree.copy_global_to(guild=guild)
        synced = await bot.tree.sync(guild=guild)
        print(f"🔄 تم مزامنة {len(synced)} أمر")
    except Exception as e:
        print(f"❌ خطأ: {e}")

@bot.command()
async def sync(ctx):
    guild = discord.Object(id=GUILD_ID)
    bot.tree.copy_global_to(guild=guild)
    synced = await bot.tree.sync(guild=guild)
    await ctx.send(f"✅ تم مزامنة {len(synced)} أمر!")

@bot.tree.command(name="broadcast", description="يفتح نموذج لإرسال رسالة خاصة لجميع الأعضاء")
async def broadcast(interaction: discord.Interaction):
    if ALLOWED_ROLE_ID not in [role.id for role in interaction.user.roles]:
        await interaction.response.send_message("❌ ما عندك صلاحية.", ephemeral=True)
        return
    modal = BroadcastModal()
    await interaction.response.send_modal(modal)

@bot.tree.command(name="setup-apply", description="يرسل رسالة التقديم على الإدارة")
@app_commands.checks.has_permissions(administrator=True)
async def setup_apply(interaction: discord.Interaction):
    if ALLOWED_ROLE_ID not in [role.id for role in interaction.user.roles]:
        await interaction.response.send_message("❌ ما عندك صلاحية.", ephemeral=True)
        return

    embed = discord.Embed(
        title="مواد الشرطة | SP8",
        description=(
            "إدارة سيرفر **SP8** تعلن عن فتح باب القبول والتقديم على الإدارة "
            "لمن لديه رغبة بالإلتحاق بعالم الإدارة نرجو تعبئة استمارة التقديم"
        ),
        color=0x2F3136
    )
    embed.set_footer(text="SP8 System | اضغط الزر أدناه للتقديم")
    
    await interaction.response.send_message("✅ تم إرسال رسالة التقديم.", ephemeral=True)
    await interaction.channel.send(embed=embed, view=ApplyView())

# ========== التشغيل ==========
bot.run(TOKEN)

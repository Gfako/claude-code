Channel: #product-changelog (C029EFJ65NF)

Liam Connerton: Hi all, one last Friday update from the growth team on another test we've launched:

*2nd Session: Welcome Modal | Non-creators*
• [<https://www.notion.so/synthesia/2nd-Session-Welcome-Modal-Users-that-never-created-a-video-327c16d22bf180bc8df4c2423bfa4615?source=copy_link%7CPRD|PRD>]
• *Outline:*
    ◦ ~65% of Enterprise users create a video within their first 14 days. To improve this, we are testing the introduction of a full-screen welcome modal on second login for users who have not yet created a video, providing clear paths to drive first video creation.
    ◦ We are also planning to launch a follow-on variation next week for users who have _created but not generated_, targeting another key drop-off in the first 14-day funnel.
• *Setup:* 50/50 A/B test
• *Scope:* New Enterprise and Self-Serve Paid users (2nd login with zero videos created)
• *Primary Metrics:* D14 Video Creation/Generation Rates, D14 Watchers
*Responsible Team:* <@U09MBDRPR7X|Péter Csóka> <@U05LKR2CJ8K|Stefano De Rosa> <@U0AD707URLG|Deniz Dirim> <@U08Q1EUR0RH|Michalis Theodosiou> <@U0AD714JV7S|Anna King> <@U0A937K6Q9M|Sara Gattoni> <@U09B62FUNQH|Liam Connerton> [2026-04-24 17:56:37 EEST]

Liam Connerton: Hi all, sharing update on a new Growth test launched:

*Create CTA: 3-path modal*
• [<https://www.notion.so/synthesia/Create-CTA-3-path-modal-Assistant-first-348c16d22bf1814a8774e6a7a2ab1dbc?source=copy_link|PRD>]
• *Outline:*
    ◦ For new users, analysis shows that starting from Template or Blank has the lowest 1st video generation rates (~17–23% CVR) across all creation paths. The current primary blue “Create” CTA across Product Home predominantly funnels users into these lower-conversion paths by launching the template picker modal. 
    ◦ In this test, we are introducing an interstitial modal triggered from the “Create” CTA, which gives users clearer entry points into different creation paths: Assisted Creation, File Upload, or Template/Blank.
    ◦ By surfacing higher-converting paths, we are aiming to improve video creation and generation rates, and overall activation.
• *Setup:* 50/50 A/B test
• *Scope:* _New_ Enterprise and Self-Serve Paid users
• *Primary Metrics:* D14 Creation/Generation Rate, D14 Watchers
*Responsible Team:* <@U09METQEZ18|Aodhagan Murphy> <@U05LKR2CJ8K|Stefano De Rosa> <@U0AD707URLG|Deniz Dirim> <@U09MBDRPR7X|Péter Csóka> <@U08Q1EUR0RH|Michalis Theodosiou> <@U0AD714JV7S|Anna King> <@U09B62FUNQH|Liam Connerton> <@U07U49BTN2D|Damian Sacco> <@U0A937K6Q9M|Sara Gattoni> [2026-04-24 15:48:03 EEST]

Sundar Solai: *Update:* Low-quality default voices removed for v3 Avatars
*What changed:* We removed the default voice recommendations for ~150 old stock avatars (v3 avatars), which now collectively use the Synthesia-wide defaults instead
*Why:* These legacy avatars were largely associated with low-quality voices, degrading users' perception of our video quality
*What's next:* We will be continuously improving the system-wide and avatar-specific default voices to steer users toward highest quality
*Feedback:* <#C032K0V8FR8|feedback-voices>
*Responsible team:* <@U067FG845L4|David Pribil> <@U06DHBNBJTA|Sundar Solai> [2026-04-24 11:53:07 EEST]

Varvara Golubeva: *No More Blurry Hands Update* :bye2:
_(also known as Multi-Ref Support for Stock Compositions)_

*Description:* Express-2 avatars sometimes have blurry hands and sleeves, along with unexpected artefacts like rings or manicure appearing out of nowhere. We're now adding an additional reference image to every composition so the model understands how hands should look and can render them clearly (no artefacts, no "tiny hands effect"). This update will also slightly improve lipsync for avatars.

*Why it matters:* This will increase overall video quality and save time for our users by reducing the need to regenerate videos.

*Limitations:*
Currently only available for *14* home compositions of stock customisable avatars (Sarah, Claire, Luke, Daniel, Hope, Carol, Bruce, Steve, Natasha, Clint, Dorothea, Inna, Finlay and Larry). Will be rolled out to more avatars and compositions soon fixing blurriness issues for more avatars.

*Plans:* All plans
*Responsible team:* <@U04913K08A0|Harsh Puri> <@U08EPMSMTEX|Hyojong Kim> <@U91510N9M|Karel Lebeda> <@U06CRKU7FLM|Matteo Maggioni> <@U04UM7K7XV3|Adam Cutmore>
*Feedback:* <#C01AVJ292F5|feedback-avatars> [2026-04-23 13:50:20 EEST]

Varvara Golubeva: *Name:* New Customizable Avatars (Amazing 4) and New Voices :heart:

*Description:*
We’re introducing 4 brand-new Express-2 avatars. Larry, Finlay, Dorothea and Inna. All avatars are paired with voices.

Finlay, Inna and Larry have *new* voices paired with them. Dorothea was paired with existing voice.

*Why it matters:* we want to give users more avatar variety and more creative options (and inspire them!)

*Limitations:*
• Voice, lip sync, facial expressions, and body language behavior follow the current Express-2 avatar system. For all of them we will also add ref image, so these avatars will not have blurry hands issue when launched. 
*Plans:* All plans
*Feedback:* <#C01AVJ292F5|feedback-avatars>
*Thanks to everyone involved* <@U06DHBNBJTA|Sundar Solai> <@U0876P2CK38|Allyson Pemberton> <@U04KZ5NFCG5|Josh Baker-Mendoza> <@U08EPMSMTEX|Hyojong Kim> [2026-04-22 16:37:00 EEST]

Tom Bennet: Hey team, excited to share an update on *voice cloning* :microphone:

*What changed:* The standalone voice cloning flow has historically been limited to Enterprise users - self-serve users only had access via Personal Avatar creation. Instead, *it's now available to all users including freemium* :globe_with_meridians: All Synthesia users can create voices _outside_ of the personal avatar creation flow.
*Why:* The release of <https://synthesia.slack.com/archives/C029EFJ65NF/p1776755558357909|Personal Avatars 2.5 on mobile> means that users can create avatars _without_ a dedicated voice. Enabling voice cloning for everyone means they're now able to easily add a voice afterwards. It also makes us more competitive than HeyGen in terms of our offering here.
*What's next*: With all users now able to clone their voice, we're planning to make this flow available on mobile too - work is in progress and I'll follow up with another update soon.
*Release notes*: <https://www.notion.so/synthesia/Voice-cloning-for-all-plans-dd0c16d22bf1822d9dde017807f222c2?source=copy_link|Release notes>
*Feedback:* <#C032K0V8FR8|feedback-voices>
*Responsible team:* <@U06DHBNBJTA|Sundar Solai> <@U0876P2CK38|Allyson Pemberton> <@U05NPB89TBL|Mairtin O'Sullivan> <@U01JALSQXDX|Adam Chelminski> <@U05JDFHT2V8|Brian Briscoe> <@U09MBDRPR7X|Péter Csóka> :clapping_all: [2026-04-22 13:57:47 EEST]

Liam Connerton: *Hi all, sharing update on a new Growth test launched:*

*Onboarding: Updated Welcome Modal Creation Paths*
• [<https://www.notion.so/synthesia/Onboarding-Welcome-Modal-Creation-Paths-327c16d22bf1803f91a3f9b462a918ba?source=copy_link|PRD>]
• *Outline:* 
    ◦ Data shows that the highest converting create-to-generate paths for first video creation are AI Assistant and File Upload.
    ◦ In the current onboarding welcome experience, users are provided with a mix on options to get started with: AI Assistant, Personal Avatar Creation, or Video Duplication.
    ◦ We are testing an updated welcome experience which prioritises our highest converting paths (_AI Assistant and File Upload)_, with the aim of increasing first video generation rates and user activation.
• *Setup:* 50/50 A/B test
• *Scope:* New Enterprise & Self-Service Paid users
• *Primary Metrics:* Video Creation/Generation Rates, D14 Watchers
*Responsible Team:* <@U09MBDRPR7X|Péter Csóka> <@U05LKR2CJ8K|Stefano De Rosa> <@U0AD707URLG|Deniz Dirim> <@U09B62FUNQH|Liam Connerton> <@U0A937K6Q9M|Sara Gattoni> <@U08Q1EUR0RH|Michalis Theodosiou> <@U0AD714JV7S|Anna King> [2026-04-22 11:43:25 EEST]

Tom Bennet: Morning team - excited to share that Personal Avatar creation is now live for mobile users :selfie::fire:

This was a key gap in our mobile experience. We shipped the mobile MVP without any avatar-based flows, and avatar creation is one of the highest-intent actions a new user can take. As of today, self-serve users on mobile can generate a new express-2 Personal Avatar on their mobile device using the selfie camera or a photo upload.

*Why avatars?* :avatar-alex: 
For the <https://www.notion.so/synthesia/The-Mobile-Bet-TOF-Growth-Vision-Strategy-326c16d22bf180fe9d46f154433b3578|mobile bet>, we're taking the approach of shipping rapid incremental improvements, unlocking the Synthesia experience gradually. Shipping avatar creation will unblock our marketing and SEO teams from testing top-of-funnel activation, sending new users _directly_ into the avatar creation experience (including on freemium). We also anticipate it'll provide a powerful way to engage new users on the platform and guide them towards the creation experience.

*What's next?*
• Personal Avatar customisation on mobile (outfit creation - sneak preview of designs <https://www.figma.com/design/NtA0jZPHInc173MPjb03cy/Growth-Design-in-product?node-id=15119-156446&t=uR3WgYindBMTqkde-4|here>) :necktie: 
• Voice cloning on mobile :mega: 
• Video creation on mobile with Assistant and storyboard view :eyes: 
Big thanks to the team who made this happen <@U09METQEZ18|Aodhagan Murphy> <@U05LKR2CJ8K|Stefano De Rosa> <@U05JDFHT2V8|Brian Briscoe> <@U07DBTKACER|Marcelo Savignano> and to the wider Growth team. Shout outs to <@U06DHBNBJTA|Sundar Solai> <@U059L7HACMV|Martin Davies> <@U09QCRXEPAN|Thomas Wittek> for their support and feedback throughout. [2026-04-21 10:12:38 EEST]

Sara Gattoni: Hello :wave:
Sharing an update on a new test experience we've rolled out as baseline:

*“Preview Modal: Drive users to generate”* → [<https://www.notion.so/Preview-Modal-Drive-users-to-generate-319c16d22bf180139ca2c8cd9705ae18?v=2fec16d22bf1804288b2000c2d926695&source=copy_link|PRD>, <https://app.snowflake.com/xeevkzp/ah84908/#/streamlit-apps/STREAMLIT_APPS.APPS.EXPERIMENT_BAYESIAN_BUDDY?loginAfterSessionExpired=true&streamlit-experiment_id=7478b0aa-0d71-4af8-a3fd-f5c50774f03a|Bayesian Buddy>]

Results:
:point_right::skin-tone-3: Users are more likely to generate, watch and publish their self generated video; Uplift is coming from generation, not net new watchers. Of users that generate, they are also more likely to come back and generate again :star-struck:

*Enterprise users:*
• 1d Generation: +5.7% (~100% CtW), stag sig 
• 3d Generation: +4.8% (~100% CtW), stag sig 
• 1d Self-Generated Watch: +5.7% (~99.7% CtW) 
• 3d Self-Generated Watch: +4.2% (~98.7% CtW) 
• 1d Video Published: +6.25% (~95.5% CtW) (with corresponding decrease in share)
• 1d 2nd Generation: +7.02% (~99.4% CtW), stag sig
• 3d 2nd Generation: +4.78% (~99.8% CtW), stag sig
*Self-serve users:* 
• 1d Generation: +2.47% (~90% CtW), stag sig 
• 3d Generation: +2.16% (~90% CtW), stag sig 
• 3d Self-Generated Watch: +2.39% (~87% CtW) 
• 1d 2nd Generation: +6.43% (~98% CtW), stag sig
• 3d 2nd Generation: +3% (~94% CtW), stag sig
Note: the metrics show a slight decrease in avg num videos generated, but since 2nd generation is up we believe this is due to outliers in the control.

*The experiment was released to 100% of self-serve paid and Enterprise users* :rocket:
*Thank you team!*
<@U09MBDRPR7X|Péter Csóka> <@U08Q1EUR0RH|Michalis Theodosiou> <@U0AD714JV7S|Anna King> <@U0AD707URLG|Deniz Dirim> <@U09B62FUNQH|Liam Connerton> <@U0A937K6Q9M|Sara Gattoni> <@U05NPBAH6E6|Theo Djerkallis> <@U08V1QDPGNN|Jack Drew> <@U05LKR2CJ8K|Stefano De Rosa> <@U07U49BTN2D|Damian Sacco> [2026-04-17 15:24:26 EEST]

Nikola Zdravkov: Hi team - sharing update on new enterprise routing test we've launched :chart_with_upwards_trend:

*Feature Highlights* 
• [<https://www.notion.so/synthesia/SS-users-100k-ARR-Accounts-routing-modal-336c16d22bf180c0a127d42f8f6e7c4a?v=8a6c44d0678d4c60a7f7d141f4dbe5f9&source=copy_link|PRD>]
• *Outline:* We're testing whether informing users during onboarding that their company has an existing enterprise agreement increases PQL handraiser conversion and pipeline generation. 
• We are showing an awareness modal before ai assisted onboarding for any SS plan users from account domains with >100k ARR in salesforce.
• *Setup:* 50/50 A/B <https://app.optimizely.com/v2/projects/5173948275490816/results/9300002359725/experiments/9300003106902?baseline=1700187&currency=DOLLAR|test>, (<https://app.eu.amplitude.com/analytics/synthesia/dashboard/e-lnaza0ji|amplitude>)
• *Scope:* SS users (Self-Service Paid, Freemium, >100k ARR account domains in SFDC)
• *Primary Metric:* Handraiser demo reqeusts, Handraiser Opps created
    ◦ *Guardrail metric:* 1st video creation rate, 1st video gen rate
*Responsible Team:  <@U05LKR2CJ8K|Stefano De Rosa>* *<@U05JDFHT2V8|Brian Briscoe>* *<@U09B62FUNQH|Liam Connerton>* *<@U07U49BTN2D|Damian Sacco><@U06CUE57N1Z|Chris Mee>*  [2026-04-16 18:37:47 EEST]

Liam Connerton: Hi all – following our T1 pricing test (run Feb–Mar 2026), we're rolling out the new lower price points across T1 markets for both new and existing users for Starter/Creator plans.

In testing, the lower prices drove a meaningful increase in Sales Qualified Opportunities, particularly in the Enterprise segment, while keeping self-service revenues stable.

*Rollout Plan:*
• _New users_ – new prices are now live for 100% of users signing up in the following T1 Geo's (US, UK, DE, FR, CA, NL, CH) as of today
• _Existing users_ – new prices will be reflected in in-app experiences (plan picker, upgrade/downgrade flows) by Friday 17th April
More details on scope, price points, and <https://www.notion.so/synthesia/T1-Pricing-Rollout-Plan-33cc16d22bf181b195a1e9aa8f8c87a2?source=copy_link|rollout here>.

Thanks to everyone involved - <@U05JDFHT2V8|Brian Briscoe> <@U0352G4TPMH|Veselin Nikolaev Velkov> <@U05LNBUBPQC|Viggo Widoff> <@U04EB5JGNK1|Cormac Keane> <@U091NFEN4J0|Michael London> <@U0A7M12MYQ0|Gwen Morvan> <@U07U49BTN2D|Damian Sacco> <@U09B62FUNQH|Liam Connerton> <@U08Q1EUR0RH|Michalis Theodosiou> <@U08V1QDPGNN|Jack Drew> <@U05NPBAH6E6|Theo Djerkallis> <@U09MBDRPR7X|Péter Csóka> <@U03DNMR1EKD|Nikola Zdravkov> [2026-04-15 14:57:45 EEST]

Sundar Solai: Hi all, in Q2 you'll be hearing more from the Voice team as we improve our voice recommendations to steer users to the best defaults.

In this update, we have three improvements to report:
1. :broom: *Bad voices removed from stock templates:* We went through Synthesia's 120+ templates to ensure they use good voices.
2. :ladybug: *Bug in AI onboarding resolved:* There was a bug in onboarding that was incorrectly defaulting to the voice `en-GB Original`. We've eliminated this voice from onboarding so user's first impression is of a higher quality voice.
3. :jp: *Improved Japanese voice defaults:* Previously, translating a video into Japanese would try to maintain the avatar's voice (e.g. `Alex - Melodic` ). However, feedback from native speakers is that these translated versions of the avatars' voices don't sound native. Now, we prioritize native voices from the best available Japanese language provider.
*Why it matters?*
• Poor voice quality leaves a bad impression of the entire video, as measured by lower Net Promoter Score
• First time creators are more likely to use our best available voices
*What's next?*
• We will be updating the default voice recommendations across all languages to use the best available tech
• We will be updating the pairings between avatars and voices to make sure users are jointly using the best avatars & voices
*Responsible team:* <@U067FG845L4|David Pribil> <@U07DEMFUUBV|Igor Pashynnyk> <@U01JALSQXDX|Adam Chelminski> <@U06DHBNBJTA|Sundar Solai> [2026-04-14 16:58:51 EEST]

Sara Gattoni: Hello :wave:
Sharing an update on a new test experience we've rolled out as baseline:

*Auto-generating a share link on “Share” click* [<https://www.notion.so/Share-Copy-Link-generate-copy-in-1-click-Enterprise-330c16d22bf1802dbfd1c622917e6ee2?pvs=21|PRD>][<https://app.eu.amplitude.com/analytics/synthesia/dashboard/e-ftsa7y00|Dashboard>][<https://app.snowflake.com/xeevkzp/ah84908/#/streamlit-apps/STREAMLIT_APPS.APPS.EXPERIMENT_BAYESIAN_BUDDY?loginAfterSessionExpired=true&streamlit-experiment_id=3c2617c0-c203-44cd-870f-f3cacff7bd48|Bayesian Buddy>] delivered a positive shift toward publishing behaviour.
The follow up test on Enterprise users met its primary objective of increasing publishing and sharing, and is considered a win, therefore *we released it to 100% of Enterprise users* :rocket:

Results:
• Video published rate increased (+6.11% 1d, +3.6% 7d; ~97–100% CtW), alongside improvements in videos published or downloaded (+2.7% 1d, 98% CtW) and video share/collaboration requests (+11% 3d ~75% CtW)
• We have seen a decrease in download behaviour (- 6% ~10% CtW) indicating a directional shift from downloading to sharing. To note: downloads have fallen mostly among users that were already not publishing - meaning we have net gain in those that do. Also the joint metric videos published or downloaded is positive (+2.7% 1d, 98% CtW) showing that more users are interacting with their video.
• Downstream metrics (generation, retention) were flat, suggesting no negative impact on core engagement. [2026-04-10 12:52:26 EEST]

Liam Connerton: Hi all - sharing an update on a new test experience we've rolled out as baseline:

*Sharing Benefits Modal*
• [<https://www.notion.so/synthesia/Share-don-t-Download-30dc16d22bf180769028d34f3e359c20?source=copy_link|PRD>] 
• *Outline:* When users trigger a video download, we tested showing a modal that highlights the benefits of sharing instead - the download still starts automatically. Users can copy a share link, or dismiss the modal (in which case it won't reappear).
• *Test Results:*
    ◦ Video published rate: *+47%* (at 100% Chance-to-Win)
    ◦ Share page watch rate: *+15%* (at 100% Chance-to-Win)
    ◦ Number of unique videos published: *+33%* (at 99.5% Chance-to-Win)
    ◦ Video generation rate: *+3.4%* (at 98% Chance-to-Win) 
    ◦ Download rates remained flat, indicating sharing gains came without cannibalising existing download behaviour
 • Now rolled out as baseline experience for Self-Serve Paid & Enterprise users

 *Thanks team -* <@U08EGJREK2A|Adam Gómez> <@U05LKR2CJ8K|Stefano De Rosa> <@U0AD707URLG|Deniz Dirim> <@U08Q1EUR0RH|Michalis Theodosiou> <@U09MBDRPR7X|Péter Csóka> <@U07U49BTN2D|Damian Sacco> <@U0A937K6Q9M|Sara Gattoni> [2026-04-08 13:50:21 EEST]

Sara Gattoni: The experiment is now released for Enterprise users [<https://www.notion.so/synthesia/Share-Copy-Link-generate-copy-in-1-click-Enterprise-330c16d22bf1802dbfd1c622917e6ee2?v=2fec16d22bf1804288b2000c2d926695&source=copy_link|PRD>][<https://app.eu.amplitude.com/analytics/synthesia/dashboard/e-ftsa7y00|Dashboard>][<https://app.snowflake.com/xeevkzp/ah84908/#/streamlit-apps/STREAMLIT_APPS.APPS.EXPERIMENT_BAYESIAN_BUDDY?loginAfterSessionExpired=true&streamlit-experiment_id=3c2617c0-c203-44cd-870f-f3cacff7bd48|Bayesian Buddy>] :rocket: [2026-04-02 16:11:12 EEST]

Sara Gattoni: The test met its primary objective of increasing publishing and sharing, and is considered a win, therefore we released it for both freemium and self-serve paid users :rocket:

Auto-generating a share link on “Share” delivered a positive shift toward publishing behaviour.
• Video published rate increased (+2.6% 1d, +2.3% 3d; ~92–95% CtW), alongside improvements in videos published and viewed on the share page (+4.2% 1d, +4.6% 3d; ~92–94% CtW). 
• Download behaviour remained broadly neutral to slightly up, indicating a directional shift from downloading to sharing without harming overall usage.
• Downstream metrics (generation, retention) were flat, suggesting no negative impact on core engagement.
• A small but statistically significant decline in share/collaboration invite rates was observed for self-serve users, which requires further investigation.
A follow up test is about to be released for the Enterprise segment. [2026-04-02 15:01:03 EEST]

Maurizio Pireddu: *Name:* Script Remediation Guidance to GA :rockets_fire:

*Description:* Guidance that helps users identify and fix script issues before video generation - now generally available for all users!

*Why it matters:*
• ~59% fewer auto rejections (self-serve & freemium)
• 2.39% increase in video creation (7 days, self-serve & freemium) 
• No negative impact on user engagement
Users get actionable feedback on script problems before they hit generate, leading to more successful videos and fewer rejected submissions.

*Plans:*
• Self-serve / Freemium: always on
• Enterprise: off by default, admins control enablement via workspace or org settings

*Responsible team:* <@U09TCTK7Q1G|Maurizio Pireddu> <@U0A9XJJ0S9F|Suraj Lukha> <@U04SGT72STD|Mike McDonald>  <@U0A0JGJJZL3|Steve Keogh>

*Feedback:* <#C04AT2B20PQ|feedback-enterprise> [2026-04-02 13:14:44 EEST]

Eduardo Mucelli: Hey everyone :wave: We've just rolled out a fix in production that improves timing accuracy in rendered videos

:sparkles: What it does
Rendered videos should now have more accurate timing throughout, with cleaner stitching between the different parts created during rendering

:meow_fingergunsrreverse: Why it matters
This improves the technical quality and consistency of exported videos and reduces the chance of timing-related issues in systems that fetch and use our output MP4s
Most people would not notice this during normal playback, but it makes the final MP4 more accurate and reliable

:warning: Tradeoff
As part of the fix, some exported videos may be a bit larger in file size than before

:speech_balloon: Feedback
<#C0505QXF57U|engineering-video-generation> [2026-03-31 16:31:28 EEST]

Varvara Golubeva: :clapper: *Motion Graphics in the Editor*

:clipboard: Together with Assistant, we will be launching Motion Graphics generation directly in the Editor. Users can create motion assets inside a scene based on their script, using a set of pre-baked styles.

:sparkles: *Why it matters:*
*Save time:* generate in one click a scene that would otherwise take significant time to build manually
*Boost engagement:* makes videos feel more dynamic, polished, and less like a narrated slide deck

 :rocket:  *How it works:*
Users can generate motion assets directly inside a scene, without leaving the Editor
Generation is based on the scene script, making it fast to try and easy to use
Adds sound effects, so the output feels more polished right away
Works especially well for structured formats like cards, timelines, and checklists
It will look like a media asset dropped on scene

:warning: *Limitations:*
Quality is already strong, but results can still be somewhat inconsistent;
You can't brand these assets or edit them;
Generation is currently limited to 30 seconds max for better quality (70% of scenes created in Synthesia are less than 30 seconds).

*Plans:* available across all plans.
*Feature flag:* Users with AI Media turned off will not see or be able to use this feature
*Credits consumption:* This is a _Beta_ feature, so it is free and does not consume credits. This is a first step to introduce Motion in Synthesia.

:video_camera: *Video about it and examples attached* :eye: 

Team: <@U04UM7K7XV3|Adam Cutmore> <@U07DTEULUE5|Mateusz Siek> <@U097N756FQE|Will Golledge> :heart:
Feedback: <#C093M7GQFD3|feedback-gen-media> [2026-03-31 15:36:32 EEST]

Bill Leaver: _This launch video was generated with Assistant_ :loading: 

We’re excited to announce the GA of :assistant: Assistant :assistant:, to help users create better videos, faster.

This includes substantially improved visuals and a tightened feature set, debuting *stock styles* and *motion graphics*.

Check out the launch video, script + generated assets courtesy of :assistant:: <https://share.synthesia.io/a171a49c-d298-44c3-a0c7-0530c162afe7>

_Important note_: :mega:  <https://synthesia.slack.com/archives/C0ALVCPCZV0/p1774546909606869|the big marketing push> about the new Assistant will come <https://synthesia.slack.com/archives/C0ALVCPCZV0/p1774547439922989?thread_ts=1774546909.606869&cid=C0ALVCPCZV0|once we add support for some key Enterprise functionality> (branding, templates).

*Key capabilities:*
• Produces higher quality scripts with matching visuals in a video first (not ppt) style, using a new script writing framework
• Uses stock styles (:new:) to generate more consistent, polished visuals across motion graphics (:new:), avatars, b-roll, images
• Add rich context (files, URLs, prompts) during creation to improve output quality 
• Iterate via chat inside the Editor because the first output is never 100% 
*Why it matters*
• Makes video creation in Synthesia substantially simpler, helping us to capture net new users personas – especially those with limited prior video creation experience
• For these new users, Assistant solves two core problems:
    ◦ They don’t know how to create a video to solve their business need (quality)
    ◦ They know what they should create, but it takes too long (speed)
*Note for GTM* :warning:
• Previously, Assistant would replace the AI Video Assistant; now, we'll maintain both feature in parallel for a few weeks
    ◦ Why: Assistant now supports only one template – Assistant Default – which is hard coded and not exposed to the user in the creation flow
        ▪︎ Chat with Assistant is only enabled on videos created using this template; we'll expand this to all videos soon
• For customers (especially Enterprises) who are restricted to custom templates, they'll have to use the AI Video Assistant until the Assistant supports all templates (:soon: )
    ◦ Once we have parity, we'll rip out the legacy AIVA as planned 
• Credit consuming actions invoked by Assistant, like generating b-roll with Veo3, are free for the foreseeable future 
*Limitations*
• Only supports one template (Assistant Default) for now
• No support for brand kits yet, just stock styles 
• Chat-based editing only works for Assistant-created videos
• Asset generation (b-roll, motion graphics, images) can take a few minutes 
• Visual quality (especially motion graphics / b-roll) is still WIP
*Coming next*
• Quality improvements
• Unlock adoption for Enterprises with support for custom templates, brand kits, and deeper brand understanding via custom styles 
*Launch* 
• *Plans:* All
• *Pricing*: Free
• <https://www.notion.so/synthesia/Assistant-Release-Notes-278c16d22bf180ea9329c56124509a65|Full release notes>
Feedback: <#C099U0T5QBF|assistant-feedback>. For questions about release plans, ask in <#C0ALVCPCZV0|assistant-gtm>.

*Team:* <@U06QP4KFVRN|Justin Manley> <@U09R75DUVEU|Chang Feng> <@U02EKG65F8R|Ante Burazer> <@U07Q9U959PS|Andraz Hribernik> <@U041EP5UFHP|Joshua Oluwagbemiga> <@U03RVGPM6A1|Gemma Huang> <@U09AKFKFXLG|Elahe Naserianhanzaei> <@U07788TTTJR|Johannes Goslar> <@U03PPP9TUGG|Myles Jubb> <@U08HT5P2AMU|Bill Leaver> supported by <@U06507VB0EB|Varvara Golubeva> <@U04UM7K7XV3|Adam Cutmore> <@U097N756FQE|Will Golledge> <@U01FZ1B32EM|Urban Marovt> <@U0AE6SWRYTB|Jace Wade> [2026-03-31 14:49:28 EEST]

Igor Pashynnyk: *Name:* Smooth Voice Generation :butter:

*Description:* Script audio used to be generated sentence by sentence. Now we generate up to entire paragraphs in one go.

*Why it matters:*
• Voices will be more natural and less choppy; more stable volume, tone, etc.
• Short sentences will sound less abrupt
• Our voices will now sound just as good as generating the same script directly on 11Labs (whereas customers previously flagged a gap in quality)
*Limitations:*
• Not all providers support this change, but our biggest ones do (ElevenLabs, Azure, and Synthesia's Express-Voice)
• For long paragraphs, it will take slightly longer to preview the script
• Voices may sound slightly faster than before since we no longer have a fixed pause after every sentence
*Plans:* All

*Rollout plan:* gradual rollout through the end of next week, starting at 5% today

*Responsible team:* <@U07DEMFUUBV|Igor Pashynnyk> <@U067FG845L4|David Pribil>

*Share feedback in:* <#C032K0V8FR8|feedback-voices> [2026-03-31 14:19:25 EEST]

Sara Gattoni: Hi all – sharing an update on a new growth test we’ve launched :rocket:
*“Preview Modal: Drive users to generate”* → [<https://www.notion.so/Preview-Modal-Drive-users-to-generate-319c16d22bf180139ca2c8cd9705ae18?v=2fec16d22bf1804288b2000c2d926695&source=copy_link|PRD>, <https://app.snowflake.com/xeevkzp/ah84908/#/streamlit-apps/STREAMLIT_APPS.APPS.EXPERIMENT_BAYESIAN_BUDDY?loginAfterSessionExpired=true&streamlit-experiment_id=7478b0aa-0d71-4af8-a3fd-f5c50774f03a|Bayesian Buddy>]

*Outline:*
Today, only about 60% of new enterprise users generate videos, even though many preview a video before their first generation. We’re testing new generation CTAs in the editor preview flow to encourage users to generate while they’re previewing, or right after they finish previewing, their video.

*In the variant:*
• While users are watching the video preview, they see a persistent *“Generate”* CTA
• At the end of the video preview, users see 2 CTAs: *“Back to edit”* and *“Generate Video”*
• These prompts are shown in the editor preview experience to encourage generation at a high-intent moment
• When a user clicks on the new "*Generate*" or "*Generate Video*" CTAs we run all the normal checks for errors/moderation and provided that those don't fail the generation will start automatically. In case of errors or moderation issues the users will still see generation options before the generation starts, as we normally do.

*Primary Metrics:*
Video Generation Rate
1D / 7D generation rate

*Setup:*
Desktop – 50/50 A/B test
Signup entry: Editor, upon video preview click

*Audience:*
Live for New and Existing Paid Self-Service and New and Existing Enterprise users.

*Goal:*
Increase video generation by nudging users toward generation during and after preview, so more new users complete video generation earlier in their journey.

*Thank you team!*
<@U09MBDRPR7X|Péter Csóka> <@U08Q1EUR0RH|Michalis Theodosiou> <@U0AD714JV7S|Anna King> <@U0AD707URLG|Deniz Dirim> <@U09B62FUNQH|Liam Connerton> <@U0A937K6Q9M|Sara Gattoni> <@U05NPBAH6E6|Theo Djerkallis> <@U08V1QDPGNN|Jack Drew> <@U05LKR2CJ8K|Stefano De Rosa> <@U07U49BTN2D|Damian Sacco> [2026-03-31 12:19:19 EEST]

Varvara Golubeva: *Name:* New Customizable Avatars (Fabulous 4) :heart:

*Description:*
We’re introducing 4 brand-new Express-2 avatars. Claire, Daniel, Sarah and Luke.

These avatars can be used in the Editor and also will be paired in Assistant with a motion graphic style, making it easier to create more dynamic and visually polished videos right away.

*Why it matters:* we want to give users more avatar variety and more creative options (and inspire them!)

*Limitations:*
• These avatars are paired with existing voices (they are not new)
• Voice, lip sync, facial expressions, and body language behavior follow the current Express-2 avatar system
*Plans:* All plans

*Responsible team: <@U029T33J4JH|Tatiana Hristova>*  <@U08EPMSMTEX|Hyojong Kim>

*Feedback:* <#C01AVJ292F5|feedback-avatars> [2026-03-27 18:51:03 EET]

Sundar Solai: *Sora 2 retirement* :happy-retirement: :rip: :city_sunset: — *6-month notice*

As you may have heard in the news, OpenAI is shutting down their Sora video platform, including integrations like the one we have in our Media panel and AI Playground.

The retirement is scheduled for *September 24, 2026.* We expect to keep the integration running until then.

Once removed, users will still have access to the Google Veo 3.1 and Veo 3.1 Fast models. Currently, neither of these models have audio enabled, but the Product team plans on making audio optional for the Veo models before Sora is retired. Note that the Veo models will cost twice as many credits with audio enabled.

There is currently no in-product mention that Sora is retiring, but this is something else that Product expects to add in advance of September 24. [2026-03-25 18:23:33 EET]

Liam Connerton: Hi all - sharing update on a new Growth test we've launched :rocket:

*Feature Highlights While Waiting*
• [<https://www.notion.so/Feature-Highlights-While-Waiting-30dc16d22bf1807abc59dbef68175bc6?source=copy_link|PRD>]
• *Outline:* We are testing the introduction of a new *waiting experience during video generation*, replacing the current “video is generating” animation with feature highlight cards.
• This experience aims to increase feature awareness and adoption during otherwise idle time, surfacing key features (with entry points where relevant). Cards are _dynamic_ by plan, with CTAs shown or hidden based on feature availability.
• *Setup:* 50/50 A/B test
• *Scope:* All users (Enterprise, Self-Service Paid, Freemium) - desktop only
• *Primary Metric:* Feature Adoption Rate (of surfaced features)
*Responsible Team:* <@U09METQEZ18|Aodhagan Murphy> <@U05LKR2CJ8K|Stefano De Rosa> <@U09B62FUNQH|Liam Connerton> <@U0AD714JV7S|Anna King> <@U0A937K6Q9M|Sara Gattoni> <@U03NTA55L4E|Norbert Annus> <@U0AD707URLG|Deniz Dirim> <@U08Q1EUR0RH|Michalis Theodosiou> [2026-03-23 13:49:35 EET]

Sara Gattoni: Hi all – sharing an update on a new growth test we’ve launched :rocket:
“Failsafe path on Personal Avatar creation” → [<https://www.notion.so/synthesia/Failsafe-path-on-Personal-Avatar-creation-30dc16d22bf1806d8233d6d4b1fb910d?v=2fec16d22bf1804288b2000c2d926695&source=copy_link|PRD>, <https://app.snowflake.com/xeevkzp/ah84908/#/streamlit-apps/STREAMLIT_APPS.APPS.EXPERIMENT_BAYESIAN_BUDDY?loginAfterSessionExpired=true&streamlit-experiment_id=09681abe-9fac-42b7-92f5-bd9b95634780|Bayesian Buddy>]

*Outline:*
Today, a large share of self-serve paid users choose the Personal Avatar path during onboarding, but many drop off before completing the flow. We’re testing a failsafe experience that intercepts users when they try to exit Personal Avatar creation and offers them an easier path to continue by creating a video with an existing avatar instead.

In the variant:
 • When users attempts to leave the Personal Avatar flow before submission, we show an intercept modal asking to create a video with a studio avatar instead
 • When users attempts to leave during or after submission, once avatar generation has started, we show an intercept modal mentioning that the avatar will be ready soon and prompting to create a video with a studio avatar in the meantime
 • The modal is shown only once per session, and if dismissed via skip, it will not appear again

*Primary Metrics:*
• Video Creation Rate
• Video Generation Rate 
• Number of videos created/generated
*Setup:*
Desktop – 50/50 A/B test

*Audience:*
Live for New Paid Self-Service and Enterprise users who attempt to leave the Create Personal Avatar flow.

*Goal:*
Convert Personal Avatar funnel abandoners into activated video creators, so more users create and generate their first or subsequent videos.

*Responsible Team:* <@U05JDFHT2V8|Brian Briscoe> <@U05LKR2CJ8K|Stefano De Rosa> <@U09B62FUNQH|Liam Connerton> <@U07U49BTN2D|Damian Sacco> <@U0A937K6Q9M|Sara Gattoni> [2026-03-19 17:42:58 EET]

Tom Bennet: Morning team - excited to share that our *mobile experience* is now rolling out to *100% of self-serve and freemium users* :calling: :fire:

We launched the 50:50 split test just over 2 weeks ago and have been shipping rapid, iterative improvements since. Early signals show the experience is resonating, with increased early engagement and retention:
1. *Share of returning users* (after first session) is up 36% [14.8% to 20.2%]
2. *Average session duration* in the first 24h is up 66% [7.6 min to 12.6 min]
3. *Paid plan upgrade rates* are all trending between flat vs a modest increase
We're now rolling out this experience to all customers as the new baseline. From here, we’ll continue iterating on and expanding mobile journeys, while retiring legacy mobile pathways we’ve relied on historically. In terms of what's coming next:
• Personal avatar creation and customisation
• Video assistant v2 (join our <#C0AJJ0PTNNT|hackathonmarch2026> team! Search "_Mobile Storyboard Editor + Assistant_")
• Functionality for enterprise customers
Massive shout outs to <@U09METQEZ18|Aodhagan Murphy> <@U05LKR2CJ8K|Stefano De Rosa> <@U05JDFHT2V8|Brian Briscoe> <@U08Q1EUR0RH|Michalis Theodosiou> <@U0AD714JV7S|Anna King> <@U07U49BTN2D|Damian Sacco> and the whole of the Growth team :chart_with_upwards_trend: :rocket-synthesia: [2026-03-19 13:32:28 EET]

Sundar Solai: The following change was actually launched yesterday alongside the Avatar transparency launch above. Posting now though so it's documented:

*Name:* Remastered Express-2 Avatars (Natasha, Hope, Carol, Clint, Bruce, Steve)
*Description:*
• The base images of the 6 customizable stock avatars are getting a refresh
• Their skin, lightning, and overall picture quality should appear more realistic/sharper
*Why it matters:*
• Addresses feedback that these avatars looked cartoonish previously
• Unblocks a follow-up change to enable transparent backgrounds with these avatars
*Limitations:*
• The *old images of these avatars will no longer be accessible to users and will get replaced with the new ones* :bangbang: :fyi: 
    ◦ This includes all images of these avatars wearing their default outfits, situated in one of Synthesia's stock spaces
    ◦ Other images of these avatars wearing custom outfits or situated in custom spaces will remain unchanged
• This change does not address lip sync, facial expressions, or body language, which we are working with RnD on separately
*Plans:* All plans
*Responsible team:* <@U04UM7K7XV3|Adam Cutmore> <@U08EPMSMTEX|Hyojong Kim> <@U029T33J4JH|Tatiana Hristova> <@U06507VB0EB|Varvara Golubeva> <@U8M1GCU92|Corneliu Ilisescu> <@U06DHBNBJTA|Sundar Solai>
*Feedback:* <#C01AVJ292F5|feedback-avatars> [2026-03-19 12:23:29 EET]

Hyojong Kim: *Name:* Transparent Background Avatars (Express-2) :sunglasses: :mirror:
*Description:*
• Remove the background from Express-2 avatars (both Stock and Personal) and use them on top of other canvas elements
• Bonus: Add a solid color or gradient background to an avatar
*Why it matters:*
• This is the *top feature request for Express-2 avatars*
• Users previously found it challenging to use avatars with baked in backgrounds in scene layouts with many layers
• Now it's easier to replace Express-1 and older avatars with Express-2 avatars
*Limitations:*
• In some cases, you may notice the green screen we're removing is not entirely removed, leading to fuzziness along the edges of the avatar
• Rendering times may be ~7% longer
• The oldest Express-2 avatars are not supported (Ada, Ryan, Zola, Michael, Joshua, Ellie, Santa)
*Plans:* All plans
*Responsible team:* <@U08EPMSMTEX|Hyojong Kim>,<@U03NTA55L4E|Norbert Annus>, <@U04UM7K7XV3|Adam Cutmore>, <@U059L7HACMV|Martin Davies>, <@U05NPB89TBL|Mairtin O'Sullivan>, <@U06DHBNBJTA|Sundar Solai>
*Release notes:* <https://www.notion.so/synthesia/Transparent-Background-Avatars-30ac16d22bf180b1b841ff579cbb22f7?source=copy_link|Release notes here>
*Share feedback in:* <#C01AVJ292F5|feedback-avatars>
*Target launch date:* We are at ~10%~ ~40% (24 March)~ ~70% (25 March)~ 100% (26 March) now, and will release gradually to larger audiences from Tuesday onwards targeting full release by Thursday, 26th of March. [2026-03-18 19:43:11 EET]

Yury Tomilin: Hey everyone :wave:

We've just rolled out *Audio Graph* externally -- an upgrade to how audio is mixed during editor preview playback

:sparkles: *What it does*
When an actor is speaking, background music and video elements now automatically get quieter, just like in the final rendered video. Previously, the editor preview didn't do this, so what you heard while editing didn't always match the export

:meow_fingergunsrreverse: *Why it matters*
Less surprises at export time!

:warning: *Troubleshooting*
For any audio-related issues, disabling the `enableAudioGraph` feature flag should be the first thing to try

:speech_balloon: *Feedback*
<#C04LEPXQW4X|feedback-general> [2026-03-17 17:39:49 EET]

Devesh Jadon: Hi Team — we're excited to announce Upload Screen Recording! :new: :sparkles:

Check out the launch video created with :assistant: Assistant :assistant:: <https://share.synthesia.io/899551d8-7d82-4fa2-b3c7-bd09611ed0bd>

*Name: Upload Screen Recording*

*Description:*
Upload an MP4 of a screen recording — from Camtasia, QuickTime, Loom, or any tool you already use — and get a transcribed, editable Synthesia video with scenes automatically created from the content.
• Instructional Designers: Upload an MP4 and get a clean, multi-scene editable video ready to polish and publish. Any voiceover from the SME is transcribed.
• SMEs: Record once in the tool you know, share the MP4, and let your ID team turn it into training. 
*Why it matters:*
Most systems training today is recorded outside Synthesia, but importing that footage previously meant losing voiceover and rebuilding scripts manually. This is solved with Upload Screen Recording, which turns an externally created MP4 into transcribed, editable Synthesia scenes. This is especially powerful for customers who are dependent on external tools, recordings shared by SMEs who don't use Synthesia, or those who do not have approval to use our AI Screen Recorder.

*How to use it:*
In the Editor: Record → Upload Screen Recording (MP4)

*Coming soon:*
Upload an MP4 from the homepage to start a new video directly

Responsible team: <@U0A0UFEJNPN|Devesh Jadon> <@U097N756FQE|Will Golledge> <@U06FH7XLXMF|Riccardo Reale> <@U0A6SM6NH0S|Kiril Nikolov> <@U08HT5P2AMU|Bill Leaver> <@U059L7HACMV|Martin Davies>
Release notes: <https://www.notion.so/synthesia/Upload-Screen-Recording-318c16d22bf180c69684dc66bed107e1>
Plans: all
Feedback: <#C077GUL71C4|feedback-ai-screen-recorder> [2026-03-16 13:16:07 EET]

Stilla: Hi, I'm Stilla! I can help answer questions, and get work done across your <https://app.stilla.ai/settings/account/connections|connected tools>.

Tag me with @Stilla in a channel or thread when you want me to act on the messages.
:bulb: You can always continue a conversation with Stilla in the Stilla app if you want to keep the thread clean - it will be aware of any new messages in the thread. [2026-03-14 13:32:06 EET]

Devesh Jadon: Hi Team, We're excited to announce improved transcription for the AI Screen Recorder! :sparkles:

*Name: AI Screen Recorder — Improved Transcription* :writing_hand: 

*Description:*
• Record in any language and get an accurate transcript without manually selecting your language upfront
• Better pause detection: timestamps are more natural, improving scene creation quality
• Works seamlessly whether you're recording from Studio ("Upload Screen Recording") or the browser extension
*Why it matters:*
Previously, transcription relied on your browser's language settings — meaning speakers using a non-matching browser locale would often get an empty transcript and broken scene creation. Now language is detected directly from your audio, so the flow just works regardless of your browser settings.

*Limitations:*
• If detection is ambiguous (e.g. silent or non-speech audio), a manual language picker will appear as a fallback
*Plans:* Available to all users with access to the AI Screen Recorder

Responsible team: <@U0A0UFEJNPN|Devesh Jadon> <@U08HT5P2AMU|Bill Leaver> <@U06FH7XLXMF|Riccardo Reale>

Feedback: <#C077GUL71C4|feedback-ai-screen-recorder> [2026-03-13 15:11:03 EET]

Liam Connerton: Hi all - sharing an update on new test experience we've just launched :rocket:

*Editor Onboarding Journey* :bulb:
• [<https://www.notion.so/synthesia/Editor-Onboarding-Journey-28fc16d22bf180cb9bf2f1131557f6a4?source=copy_link|PRD>]
• *Outline:* For new users entering the Editor, we’ve introduced a guided *product tour checklist* to help them navigate key features and drive earlier video generation. The goal is to better support users at the start of their video creation journey and reduce the drop-off we see between video creation → generation for new users. Experience attached.
• *Setup:* A/B test
• *Scope:* New Enterprise, Self-Service Paid & Freemium users
• *Primary Metrics:* Video Generation Rate, D14 Watchers
*Thanks Team!* <@U09METQEZ18|Aodhagan Murphy> <@U05LKR2CJ8K|Stefano De Rosa> <@U05JDFHT2V8|Brian Briscoe> <@U0AD707URLG|Deniz Dirim> <@U08Q1EUR0RH|Michalis Theodosiou> <@U04GU2XJBK9|Klemen Oslaj> <@U041EP5UFHP|Joshua Oluwagbemiga> <@U0A937K6Q9M|Sara Gattoni> <@U09B62FUNQH|Liam Connerton> <@U06507VB0EB|Varvara Golubeva> [2026-03-13 14:50:38 EET]

Sara Gattoni: Hi all – sharing an update on a new growth test we’ve launched :rocket:
*“Share: Copy Link (generate + copy in one click)” →* [<https://www.notion.so/synthesia/Share-Copy-Link-generate-copy-in-1-click-30dc16d22bf18099a660c13c2c9721e8?v=2fec16d22bf1804288b2000c2d926695&source=copy_link|PRD>][<https://app.eu.amplitude.com/analytics/synthesia/dashboard/e-oprqq9t5|Dashboard>][<https://app.snowflake.com/xeevkzp/ah84908/#/streamlit-apps/STREAMLIT_APPS.APPS.EXPERIMENT_BAYESIAN_BUDDY?loginAfterSessionExpired=true&streamlit-experiment_id=1d4aa253-4067-495e-bebc-9c26db93bb8c|Bayesian Buddy>]

*Outline:*
Today, in the share modal, the primary CTA is *“Create link”*. Users click once to create the share link, then need to click again to copy it. We’re testing a streamlined flow where we change the CTA copy to *“Copy link”* and make that single click *generate the link + copy it immediately*.

In the variant:
• CTA changes from *“Create link”* to *“Copy link”*
• Clicking *“Copy link”* will: generate a share link + copy it to clipboard in the same action
• Net: *1 click instead of 2* to get a shareable link

*Primary Metrics:*
Video Published Rate

*Setup:*
Desktop – 50/50 A/B test

*Audience:* Live for *Freemium + Self-Serve* users.
Note:  we want to validate impact with safe segments first, then expand to Enterprise if results look good.

*Goal:* Reduce friction in sharing so more users successfully publish and share their videos
*Thanks team! <@U09MBDRPR7X|Péter Csóka>* *<@U08Q1EUR0RH|Michalis Theodosiou>* *<@U04SE3FMSMB|Armughan Ahmad Khan>* *<@U0230ACBZEY|Oleksandr Zastupailo>* *<@U09B62FUNQH|Liam Connerton>* *<@U07U49BTN2D|Damian Sacco>* *<@U08Q1EUR0RH|Michalis Theodosiou>* :pray::skin-tone-2::rocket: [2026-03-13 12:39:09 EET]

Catalina Oyaneder: :wood: *Audit Logs: Acting User now shown for Billing Credit Events*

Billing-related audit events (e.g. "Consumed 50 credits to dub a video") used to always show *System* as the Acting user, making it hard to tell who triggered the action.

The Acting user column now shows the real person who initiated credit-consuming actions!

:sparkles: *Why it matters:*
• Admins can instantly see who triggered a credit consumption event
• No more "System" dead-ends when investigating billing usage
• Makes Audit Logs meaningfully more useful for accountability and usage visibility
:rocket: *How to try:*
1. Go to Organization Settings → Billing → Audit Logs
2. Filter by Billing Credits Consumed
3. The Acting user column now shows the actual user (name + email) instead of System
*Notes:*
• Background/system-initiated jobs will still show System, only user-triggered actions are attributed
• *Past events* will continue to show System. Audit events are immutable and won't be backfilled [2026-03-12 13:52:53 EET]

Liam Connerton: Hi all - this morning we rolled out support for Start/End Frame image uploads in AI Playground :rocket:

*What’s new:*
Users can now upload an image and use it as a starting frame, or as both a start and end frame, alongside a text prompt to guide video generation.

*Supported file formats:* PNG, JPG, WebP

*Plan availability:*
Start/End Frame is available for Self-Service Paid (Starter/Creator) and Enterprise users. Freemium users will be guided to upgrade to access this feature.

Thanks to the team for getting this shipped :raised_hands: <@U05JDFHT2V8|Brian Briscoe> <@U0AD714JV7S|Anna King> <@U08Q1EUR0RH|Michalis Theodosiou> <@U06DHBNBJTA|Sundar Solai> <@U04UM7K7XV3|Adam Cutmore> <@U05NPB89TBL|Mairtin O'Sullivan> [2026-03-12 12:01:16 EET]

Varvara Golubeva: Hey everyone! This is my first post in the changelog about a new feature :face_holding_back_tears::heart:

*Update:* We’ve added *Button* and *Menu* as ready-to-use elements, and surfaced *Interactivity* and *Dynamic Captions* right in the Editor.

*Description*: You can now add CTAs and Menus in seconds — drop in a Button or Menu element without building it from scratch. Both interactive elements and Dynamic Captions automatically pick up your Brand Kit colours and fonts.

*Why this matters:*

*For customers:*
• *Save time on video creation:* no more re-adding “shape + text” every time you need a CTA. Also all elements are following the BK guidlines.
• *No need to use other tools:* build CTAs and captions directly in Synthesia.
• *Grow engagement:* interactive elements help viewers take action and stay involved.
*For Synthesia:*
• *Better discoverability:* Interactivity and Dynamic Captions are now easy to find and use.
• *Increase stickiness to the platform:* interactive video can be watched in Synthesia player only.
*Plans:* Creator, Ent (Interactivity). Dynamic Captions

*Limitations:*
• Menus currently support *2 options per Menu element*. Need more? Just *copy + paste* the Menu to add additional options.
*Feedback:* <#C08PLV0TDCJ|feedback-interactivity> for Interactivity. If you have more ideas on surfacing hidden features -> <#C09G33E2TJS|52-weeks-of-fixes>.
*Team:* <@U07DTEULUE5|Mateusz Siek> <@U04GU2XJBK9|Klemen Oslaj> :sparkles: [2026-03-12 11:46:05 EET]

Sundar Solai: Hi all—we're excited to announce a new look and experience for creating your personal avatar! :new: :sparkles:

*Name:* Personal Avatars new creation experience
*Description:*
• The process to create an avatar is more wizard-like :mage: , walking users through each step with more context and visuals
• We've reorganized entry points to various avatar creation methods:
    ◦ Studio Avatars have a new home at the top-right of the first screen
    ◦ Request a Personal Avatar now lives on the second screen, after users select "Personal Avatar"
    ◦ The Avatar Builder remains hidden (<https://www.notion.so/synthesia/Personal-Avatars-from-Photo-2efc16d22bf1801280f1fcbeb9be2f8c?source=copy_link#2f0c16d22bf180f19065ee011c4fba32|read more here>)
*Why it matters:*
• The original UI was seeing a lot of people abandon almost right away
• We're trying to simplify the experience so everyone, including first-time users, understands the feature
*Limitations:*
• We have removed the option to upload audio to create a voice since usage of that was low
• If you create a video extremely quickly when your avatar is first ready, the voice might not be ready yet. We will we improving this experience soon
*Plans:* Personal Avatars remain available on Starter+ plans
*Responsible team:* <@U03NTA55L4E|Norbert Annus> <@U09QCRXEPAN|Thomas Wittek> <@U08EPMSMTEX|Hyojong Kim> <@U04913K08A0|Harsh Puri> <@U059L7HACMV|Martin Davies> <@U04UM7K7XV3|Adam Cutmore> <@U0AD707URLG|Deniz Dirim> <@U06DHB8GGJU|Mikhail Shapovalov> <@U06DHBNBJTA|Sundar Solai>
• This team deserves an extra shout out—if you're wondering why this launch is coming so soon after we just launched the new Personal Avatars, it's because of this team's very hard work :clapping_all: 
*Feedback:* <#C071S5K86J0|feedback-personal-avatars> [2026-03-11 19:17:46 EET]

Maurizio Pireddu: Hi everyone, we've just launched a new experiment :rocket:

*Name:* Script Remediation Guidance - Phase 2

*What* :question:
An iteration on Phase 1, which showed a ~23% relative reduction in post-generation rejections by giving users inline script guidance before generating.
In Phase 2 we're refining the UX so users feel more supported in successfully generating their videos.

*Why important* :exclamation:
Phase 1 validated that pre-generation script guidance meaningfully reduces rejections. Phase 2 builds on that success by refining the experience, making suggestions feel more natural and supportive, so users are more likely to act on them rather than feeling discouraged from generating.

*Setup:* A/B test
*Scope:* Self-serve and Freemium users
*Primary KPI:* Post-generation rejection rate
*Secondary KPIs:* Generation conversion rate, time to generate, abandon rate

*Feedback* :speech_balloon:
<#C04AT2B20PQ|feedback-enterprise> [2026-03-09 11:43:31 EET]

Varvara Golubeva: It's time! Time for *Product Update <https://www.notion.so/synthesia/Product-Update-3-2026-31bc16d22bf1808c9205f6f588183938?source=copy_link|Newsletter>*  :heart:

*In the <https://www.notion.so/synthesia/Product-Update-3-2026-31bc16d22bf1808c9205f6f588183938?source=copy_link|Newsletter> you'll find:*
:space_invader: An interactive video showcasing all the new features
:email: Email copy we’ll send from Community with <@U0713U0CHBM|Lousine Boyakhandjyan>
:motorway: Roadmap deck for Q1-Q2
:camera_with_flash: RKO recordings in case you've missed them
:spiral_note_pad: Released notes for recently added features

The features that were released externally during the last 30 days:
:heavy_check_mark: PA from Photo
:heavy_check_mark: Translation Glossary
:heavy_check_mark: Folder Sharing
:heavy_check_mark: Multiple nice fixes and UI updates as part of <#C09G33E2TJS|52-weeks-of-fixes>

Thanks to everyone working on the product side for shipping these great updates :slightly_smiling_face:

cc <!subteam^S03HFDF2UE9> <!subteam^S03HFEHTDE1> <!subteam^S062X16R2SV> [2026-03-06 16:38:18 EET]

Sara Gattoni: Hi all – sharing an update on a new growth test we’ve launched :rocket:
_“Duplicate a Team Video”_ → [<https://www.notion.so/synthesia/Replace-Playground-with-View-Team-Content-Duplicate-30dc16d22bf1801da116e544849af021?v=2fec16d22bf1804288b2000c2d926695&source=copy_link|PRD>][<https://app.eu.amplitude.com/analytics/synthesia/dashboard/e-7mtubcij|Dashboard>][<https://app.snowflake.com/xeevkzp/ah84908/#/streamlit-apps/STREAMLIT_APPS.APPS.EXPERIMENT_BAYESIAN_BUDDY?streamlit-experiment_id=8f936715-584b-41be-b169-b26df16d68a7|Bayesian Buddy>]

*Outline:*
For new enterprise users joining workspaces that already have ≥3 videos (≈70% of cases), we’re testing a new CTA in the onboarding welcome modal. Instead of pushing users to the AI Playground (as we were doing in the previous <https://www.notion.so/synthesia/Welcome-Video-paths-go-get-started-2fdc16d22bf180f1bcb9f94ac4924107?v=2fec16d22bf1804288b2000c2d926695&source=copy_link|welcome modal >test), we’ll guide them to start from a video currently available in the workspace they have joined.
In the *variant*, we replace the previous _“Generate AI media”_ CTA with: _“Duplicate a team video”_ – Start from an existing video

When selected, users will:
• Enter a modal view
• See videos already created by their team, ordered by most popular
• Be able to duplicate instantly and get redirected to the editor
*Primary Metrics:*
• 1-Day Generation Rate
• 7-Day Generation Rate
*Setup:*
Desktop – 50/50 A/B test

*Goal:*
Increase early generation encouraging duplication, and inspiring users with their teammates’ most popular videos.

*Responsible team: <@U08EGJREK2A|Adam Gómez>* <@U05JDFHT2V8|Brian Briscoe> <@U05LKR2CJ8K|Stefano De Rosa> <@U09B62FUNQH|Liam Connerton>  <@U08Q1EUR0RH|Michalis Theodosiou> <@U07U49BTN2D|Damian Sacco> <@U0AD707URLG|Deniz Dirim> :pray::skin-tone-2:

Feedback always very welcome :eyes::pray::skin-tone-2::rocket: [2026-03-05 11:21:53 EET]

Alex Balan: *just came back to this thread to announce that now 100% of EXPRESS-2 avatars are served via the high-res route* (once everybody refreshes their browser, it might take a while for _truly everybody_ to run)

Thanks to <@U07DBTKACER|Marcelo Savignano> for running a <https://eu.hex.tech/synthesia/hex/Express-2-1080p-Experiment-032QuecB0vy0SfZSfREpp4/draft/logic?view=app|very interesting analysis> on the effect it has on video utilisation (people seem to publish the hi-res videos more :party-cat:), which confirms what we already knew - the avatars look better :smile:

In terms of the upscaler, we weren't _super happy_ with how FAL provides the model (it's extremely slow, to the point where it double or triples latency). But we are making great progress at hosting the model ourselves, with improved speed! [2026-03-04 14:24:07 EET]

Sara Gattoni: Hi all, quick update on the *Welcome Video + Guided Paths* test :rocket:

Results (*Self-service users* | Test vs Control):
• *Video creation rate:* +2% - not yet stat sig
• *Video generation rate:* +1% - not yet stat sig
• *# of videos created:* +28% - stat sig
• *# of videos generated:* +17%, stat sig
• *Create Personal Avatar:* +26% - stat sig
• *Avg. day 1 session duration:* +11% - stat sig
• *Day 2-7 retention:* +6% - _almost_ stat sig
While top-level creation and generation _rates_ remain stable, we’re seeing a meaningful increase in overall output and stronger early retention.

It’s also worth noting that users now have 3 distinct paths instead of 1, and 2 out of 3 do not immediately push video creation (e.g. Personal Avatar flow, AI playground). Given this structural shift in entry points, it’s expected that immediate video generation wouldn’t necessarily increase. The fact that generation remains stable, while output, avatar creation, session duration, and retention all increase, is a strong positive signal.

*Enterprise users*
Results for Enterprise users are directionally different, so we’ll be stopping the current experiment for that cohort. We’re launching a new tailored version for Enterprise users this week to better align with their workflows and needs.

*What’s next*
• Launch and test a new tailored experience for *Enterprise users* this week
• Further iterate on CTA hierarchy on self-serve later
 [2026-03-03 14:10:54 EET]

Sundar Solai: FYI: Selfie Avatars will be retired on June 1, this is your 90-day notice :alert-siren:

*Why?*
• We have now released <https://synthesia.slack.com/archives/C029EFJ65NF/p1772447033985849?thread_ts=1770042991.422949&cid=C029EFJ65NF|Personal Avatars from Photo to all paid users>, which addresses the same user needs with a more powerful system (customize outfit, space, and add B-roll)
    ◦ ^^ *TL;DR — Use the new Personal Avatars; it's like Selfie Avatars, but better* :slightly_smiling_face:
• Our goal is to streamline avatar creation methods to reduce confusion over the available options
*What does it mean?*
• From June 1, users will not be able to create new Selfie Avatars
• Existing Selfie Avatars users have created will remain accessible _only if they were saved_
    ◦ To save a Selfie Avatar, click on it, then click the "Save to My Avatars" button
    ◦ Unsaved avatars will no longer be accessible post June 1
• Starting now, the Selfie Avatar beta is closed and we are no longer accepting sign-ups
When users access the Selfie Avatars page, they will see the attached notice.

If any questions or concerns, don't hesitate to reach out in <#C082GU4G09Y|feedback-selfie-avatars>! [2026-03-03 14:07:46 EET]

Sundar Solai: One *slight correction about Personal Avatars creation limits*—originally we said that users could create unlimited Personal Avatars from Photos. This isn't quite true:
• Enterprise users can create unlimited Personal Avatars, both from photo or from a video
• Creator plan users can create 5 Personal Avatars (either from photo or video, it's a shared cap)
• Starter plan users can create 3 Personal Avatars (either from photo or video, it's a shared cap)
Any user who creates a Personal Avatar from a Photo can _customize it into an unlimited number of outfits_.

FYI <@U09TRQQFP89|Tom Bennet> <@U0A937K6Q9M|Sara Gattoni> <@U09B62FUNQH|Liam Connerton> <@U07U49BTN2D|Damian Sacco> <@U05JDF9UQAW|Jess Diaz-Gomes> <@U069CK47ST0|Meg Farley> [2026-03-02 19:59:33 EET]

Will Golledge: *Update*: Improved avatar replacement logic :ada:

*What's changed*:
• When replacing a multicam avatar (via single replace or bulk replace), the previous avatar's _"Camera"_ will be preserved - this means that when replacing an angled zoomed avatar with another, we will automatically aim to use an angled close shot if one exists for the new avatar
• When replacing outfits or spaces we now replace the outfit/space independently. This means that when replacing an outfit, the spaces already selected on scenes will be retained (or vice versa)
    ◦ As a result of this, when adding new scenes via template, the scene template previews now show the outfit combined with the template space
• Exact details of the logic can be found here: <https://www.notion.so/synthesia/2026-Avatar-Replacement-Logic-1e3c16d22bf180849d92ca27ce2ea5d5|2026 Avatar Replacement Logic>
*Why*: The previous logic was based on strict 1-to-1 replacements and wasn't built for the Customisable Avatars data model. Limitations of the previous replacement logic led to frustrations from users where avatars weren't retaining the space/outfit/camera as they expected

*Team*: <@U06DHBNBJTA|Sundar Solai> <@U097N756FQE|Will Golledge> <@U03NTA55L4E|Norbert Annus>

*Feedback*: <#C0ABT6QUQHH|feedback-brand-customisation> [2026-03-02 18:24:16 EET]

Haitham Seelawi: *Name:* Using Voice Runtime Triton (VoRT) for Express-voice voice clone generation + TTS

*Description:*
We are now using a different underlying architecture to power Express-voice. This new architecture resembles Avatar Runtime Triton (ART), which we have been using to render our newer avatars.

*Why this matters:*
The new architecture allows us to:
• :money_mouth_face: run Express-voice more efficiently, saving money and preventing outages
• :upvote: more easily and safely deploy new updates to Express-voice
• :rocket-synthesia: run more than one model at a time, enabling support for bigger Express-voice updates
*Things to watch:*
We will be keeping an eye on Express-voice TTS latency and errors during voice clone generation. Let us know if you experience a downgrade in either of these areas.

*Feedback:* <#C09RVDNABNH|engineering-voice-runtime-triton>

*Responsible Teams / Owners:* <@U08G4DB3LSD|Ethan Brodie> <@U09DZ4CHME1|Haitham Seelawi> <@U053EBTNDA9|Sash Stasyk> <@U06QDAUMB5F|Nathanaël Perraudin> <@U01TN6KDVB3|Youssef Alami Mejjati> <@U0876P2CK38|Allyson Pemberton> <@U067FG845L4|David Pribil> <@U01JALSQXDX|Adam Chelminski> <@U07TB2Z7UKH|Dan Kelly> <@U048H0XMZ0Q|Quinn E Stoltz> <@U06DHBNBJTA|Sundar Solai> [2026-03-02 12:35:51 EET]

Sundar Solai: :100: Hi everyone—the new Personal Avatars (from Photo) are launched to 100% of users now! This means, all users can now choose between creating a fully customizable Personal Avatar from a photo or creating a Personal Avatar the old way, from a video.

Note that we are in the process of revamping the user experience to make avatar creation more intuitive, so expect some cosmetic changes likely next week. The functionality is not expected to change. [2026-03-02 12:23:53 EET]

Tom Bennet: Hey team, I've some exciting news from the Growth team! After lots of hard work, *Synthesia for Mobile is now rolling out to self-serve customers* :rocket: :rocket-synthesia: 

<https://www.notion.so/synthesia/Mobile-MVP-release-summary-313c16d22bf180de8abfcf060ce6d879?source=copy_link|Release notes and FAQs are available here>, but a few key things to bear in mind:
• This is an *MVP* targeting sign-up, onboarding flows, content consumption, and media generation via Playground and Dubbing. The video editor and Copilot/Assistant are out-of-scope.
• We are actively working on shipping new features in the fast-follow release, including some avatar experiences and a better switch-to-desktop experience. 
• We're running a 50:50 test targeting new sign-ups - not everyone will get the full mobile experience yet.
I'll share further updates and early results soon. For now, I just want to give a huge shoutout to the team that planned, designed, and built this - it was a big undertaking, particularly given the desktop-focused nature of our product to date. Awesome work <@U09METQEZ18|Aodhagan Murphy> <@U05LKR2CJ8K|Stefano De Rosa> <@U05JDFHT2V8|Brian Briscoe> <@U08Q1EUR0RH|Michalis Theodosiou> <@U07U49BTN2D|Damian Sacco> and the rest of the Growth team :hot_fire: [2026-03-02 10:58:31 EET]

Noelia de la Cruz: Hi all, today we’re replacing the underlying voice model that powers *all Express-voices,* including English Express-voice voice clones, with a new model built to support upcoming *IPA pronunciation capabilities*. We are *not* enabling IPA pronunciation controls in the product quite yet*,* this update simply prepares the foundation for that future release.

*What you can expect:* We are expecting this to have *no effect* on existing voices. This new model sounds extremely similar to the old model, so customers should not notice any change.

*Feedback:* If you do notice any changes to Express-voices or anything unexpected, please share feedback in *<#C051JFNFN9E|feedback-voice-cloning>*.

*Team Responsible: <@U02J89Q4BH8|Noelia de la Cruz>* *<@U089D8KJH2P|David Braude>* *<@U06QDAUMB5F|Nathanaël Perraudin>* *<@U065840TD38|Olly Ferguson>* *<@U06Q07N8WG3|Duygu Can Yıldızak>* *<@U05L5FVEXHV|Trevor Allen>* *<@U07E3NAQS9E|Simon Thelin>* *<@U08G4DB3LSD|Ethan Brodie>* *<@U09DZ4CHME1|Haitham Seelawi>* *<@U0876P2CK38|Allyson Pemberton>* *<@U06DHBNBJTA|Sundar Solai>* [2026-02-26 12:49:17 EET]

Allyson Pemberton: :fyi: These voices are being deleted today [2026-02-26 11:58:38 EET]

Alexei Simanchik: Hi Everyone :wave:

Today we released the second round of improvements to play and pause behavior on blocking branches in the video player.

Users can now pause the video using the on-screen control. Previously, this was only possible via keyboard shortcuts. As before, they can also restart it. Since quizzes have their own dedicated internal Reply button, the video control is now responsible only for restarting the already played segment of a blocking branch.

Next, we are planning to introduce scrubbing capability for blocking branches, as this functionality is already available on other branches. However, we first need to determine how to integrate it in a user friendly way without taking up too much space, especially as we are trying to preserve room for interactive elements while maintaining a good mobile experience.

Responsible team: <@U0940J35ADP|Alexei Simanchik> <@U05QHKA1R0X|Yury Tomilin> <@U09SXEDSGVD|Aurélie Dufour>

Please share any feedback in <#C078TA7LJ0Y|feedback-player>. [2026-02-25 17:30:38 EET]

Liam Connerton: *Tier 1 Pricing Test - Live:*
• [<https://www.notion.so/synthesia/Tier-1-Price-Test-2fec16d22bf180caa78ee7b35e62b600?source=copy_link|PRD>] 
• We’re testing reduced pricing across all self-serve plans (monthly & annual) in Tier 1 countries (excluding Japan) to assess whether lower price points increase paid unit volume and overall revenue.
• *Setup:* A/B test
• *Scope:* Self-serve users in Tier 1 countries (excl. Japan)
• *Primary KPIs:* # of Subscribers, MRR, LTV
*Responsible Team:* <@U05JDFHT2V8|Brian Briscoe> <@U0352G4TPMH|Veselin Nikolaev Velkov> <@U05LNBUBPQC|Viggo Widoff> <@U04EB5JGNK1|Cormac Keane> <@U091NFEN4J0|Michael London> <@U0A7M12MYQ0|Gwen Morvan> <@U07U49BTN2D|Damian Sacco> <@U09B62FUNQH|Liam Connerton> <@U08Q1EUR0RH|Michalis Theodosiou> [2026-02-19 15:59:58 EET]

Richie DeRobles: Hey Team,

Can we please add LightSpeed VT to the Early Access?

*ID: 5baac4db-76d8-4e3e-a2ef-c0505e21e27c* [2026-02-18 20:44:13 EET]

Richie DeRobles: is early access still available for the photo to avatar feature? I noticed the form on the page was not available [2026-02-18 20:35:59 EET]

Liam Connerton: *Tier 3 Geos Pricing Test - Live:*
• [<https://www.notion.so/synthesia/Tier-3-Annual-Plan-Price-Test-25ac16d22bf18030b1faebbb84642f56?source=copy_link|PRD>] 
• We’re testing lower _Starter/Creator_ A_nnual plan pricing_ for net new users in Tier 3 countries to better align with in-market affordability and assess whether we can unlock incremental growth in these regions via pricing.
• *Setup:* A/B test
• *Scope:* Net new users in Tier 3 countries only
• *Primary KPIs:* # of Subscribers, MRR, LTV
*Responsible Team:* <@U05JDFHT2V8|Brian Briscoe> <@U0352G4TPMH|Veselin Nikolaev Velkov> <@U05LNBUBPQC|Viggo Widoff> <@U04EB5JGNK1|Cormac Keane> <@U091NFEN4J0|Michael London> <@U0A7M12MYQ0|Gwen Morvan> <@U07U49BTN2D|Damian Sacco> <@U09B62FUNQH|Liam Connerton> <@U08Q1EUR0RH|Michalis Theodosiou> [2026-02-17 15:32:26 EET]

Sara Gattoni: Hi all – sharing an update on 2 new growth test we’ve just launched :rocket:

:one: *Welcome Video + Guided Paths* :arrow_right: [<https://www.notion.so/Welcome-Video-paths-go-get-started-2fdc16d22bf180f1bcb9f94ac4924107?pvs=21|PRD>] [<https://app.eu.amplitude.com/analytics/synthesia/space/e-jo9x3zwp/all|Dash>]

*Outline:* We’re testing a new welcome experience for new enterprise and self-service paid users only that includes a short (5–6 sec) welcome video combined with 3 CTAs to start their journey.
Users can choose between:

:point_right::skin-tone-3: *”Make a video with AI”* - redirecting to the first time video creation onboarding experience
:point_right::skin-tone-3: *”Create your AI Avatar”* - redirecting to create Personal Avatar flow
:point_right::skin-tone-3: *”Generate AI Media”* - redirecting to the existing AI Playground onboarding flow

The goal is to create a more engaging first-touch experience and drive users to select a relevant “get started” path immediately after signup.

*Scope:* New Enterprise and self-service users
*Setup:* A/B test

:two: *New* *Banner on Video Generation Page* :arrow_right: [<https://www.notion.so/Video-Generation-Page-Banner-2fbc16d22bf1809c8e50e4f05ca720ff?pvs=21|PRD>] [<https://app.eu.amplitude.com/analytics/synthesia/dashboard/e-8n93a894|Dash>]

*Outline:* We’re testing a contextual banner on the Video Generation page for new and existing enterprise users only. The banner prompts users to create their personal avatar while they’re waiting for their video to generate. The goal is to make productive use of wait time by encouraging a high-intent, high-value action that deepens engagement with the product.
This experiment explores whether introducing the personal avatar creation prompt in this moment of waiting time increases avatar creation rate and downstream retention.

*Primary KPIs:* # and % coming back on a later session/day
*Scope:* New and existing enterprise users (with 0 Personal Avatars created)
*Setup:* A/B test

*Responsible team:* <@U05JDFHT2V8|Brian Briscoe> <@U09MBDRPR7X|Péter Csóka> <@U05LKR2CJ8K|Stefano De Rosa> <@U0A937K6Q9M|Sara Gattoni> <@U09B62FUNQH|Liam Connerton> <@U07U49BTN2D|Damian Sacco> <@U0AD714JV7S|Anna King> <@U08Q1EUR0RH|Michalis Theodosiou> <@U06FH7XLXMF|Riccardo Reale> <@U91510N9M|Karel Lebeda> <@U06HFRTTXSQ|Kieran Kelk> <@U03NTA55L4E|Norbert Annus> <@U09QCRXEPAN|Thomas Wittek> <@U06DHBNBJTA|Sundar Solai> :pray::skin-tone-2::rocket: [2026-02-17 15:11:41 EET]

Andre Araujo: Hi everyone! We have released the per-corner radius feature to everyone.

*Feature name: Corner radius*

*What* :question:
This feature will allow customers to set individual border radii for each corner of rectangular base elements, such as images, rectangle shapes, videos, and SVG icons.

*Why important* :exclamation:
Customers will be able to create shapes that previously required uploading pre-edited assets. Currently customers rely on external editing software to achieve such shapes.

*Limitations*
The feature currently does not support elements other than base rectangular shapes with 4 corners.

*How to test?* :gear:
When clicking on any rectangular element you can now click a button to enable 4 different corners (this replaces the existing range input). You can also click the button again to reset back to a single border radius, in this case it will use the top-left corner as a pivot.

Please see the attached video for an example of this in action.

*Team* 
<@U0A3E8FG8KD|André Araújo>, <@U04GU2XJBK9|Klemen Oslaj>, <@U05LKR2CJ8K|Stefano De Rosa>

Please share any feedback you have in <#C0AF8E77M7B|feedback-corner-radius> [2026-02-17 13:08:04 EET]

Will Golledge: Hi all. We've just rolled out the ability to bulk remove/replace images via the Canvas to everyone!

*What is it?* :bulb:
When replacing or deleting images via the Canvas, users are now asked whether they'd like to replace or delete all matching images.
• For replacing images, this functionality is offered via the explicit _Replace image_ button and when replacing via paste.
• For removing images, this is only offered when deleting (not cutting) images.
Note: this is currently only enabled for images - we may replicate this functionality for videos in the future.

*Why does it matter?* :thinking_face:
We get frequent feedback from with regards to difficulties they face when attempting to update images across a Synthesia video (<https://synthesia.slack.com/archives/C09G33E2TJS/p1769025493714729?thread_ts=1768915755.262959&cid=C09G33E2TJS|some> <https://synthesia.slack.com/archives/C09G33E2TJS/p1761122159396719|examples>). With this change, users are able to restyle the images in a video more easily. This is particularly useful for large videos with many scenes & images.

*How to test?* :gear:
When replacing or deleting an image in the editor, if the same image exists multiple times (either within the same scene or cross-scene), users will be shown a toast prompting whether they would like to apply that change to all other matching images.

Please see the attached video for an example of this in action.

*Team*
<@U097N756FQE|Will Golledge> <@U06DHBNBJTA|Sundar Solai> <@U059L7HACMV|Martin Davies> <@U01FZ1B32EM|Urban Marovt> <@U08VAHUPMA5|Berci Kormendy>

*Feedback* :speech_balloon:
Please share any feedback you have in <#C0ABT6QUQHH|feedback-brand-customisation>. [2026-02-16 16:52:40 EET]

Thomas Wittek: The metrics are looking good and we're ramping Personal Avatars from Photo (AKA 2.0) to 50% of workspaces.
Please keep the feedback coming as we expand this launch! [2026-02-16 16:28:37 EET]

Liam Connerton: In addition to the above, sharing a few more quick updates from the Growth team on more recent launches :rocket:

:one: *AI Playground – Multi-Asset Generation*
• [<https://www.notion.so/synthesia/Playground-Multi-Asset-Generations-2fbc16d22bf18030989fc2d1c7660bb3?v=142c16d22bf180faa389000c083e645c&source=copy_link|PRD>] [<https://app.eu.amplitude.com/analytics/synthesia/dashboard/e-eim92luv|Dash>]
• We’re adding a new capability that allows users to generate multiple media assets from a single prompt within AI Playground. By enabling users to create more media faster, we can help them find a more suitable asset for their needs and accelerate overall video creation.
• *Setup:* A/B test (~1 week to assess impact, then ramp to 100%)
• *Scope:* All users (Self-Service & Enterprise)
:two: *Updated Templates During Onboarding*
• [<https://www.notion.so/synthesia/Updated-templates-during-onboarding-2d3c16d22bf180729551ef9f5688d77f?v=142c16d22bf180faa389000c083e645c&source=copy_link|PRD>] [<https://app.eu.amplitude.com/analytics/synthesia/dashboard/e-fttn0jjc|Dash>]
• We’re testing replacing the existing default AI Assistant onboarding templates with new, refreshed templates tailored more closely to the user’s selected use case. The aim is to present a higher-quality and more relevant first outline to improve activation.
• *Setup:* A/B test
• *Primary KPI:* Video Generation Rate
• *Scope:* All users (Self-Service & Enterprise)
:three: *Updated Plan Details (Self-Service users)*
• [<https://www.notion.so/synthesia/Billing-Info-Next-Plan-Pitch-2e6c16d22bf18064acdcd923cd822094?source=copy_link|PRD>] [<https://app.eu.amplitude.com/analytics/synthesia/dashboard/e-wj3crdoi|Dash>]
• We’ve redesigned the plan details section to more clearly communicate plan usage and better highlight the value of the next tier plan to promote upgrades and PQLs.
• *Setup:* A/B test
• *Scope:* Self-Service users
• *Primary KPIs:* Upgrade Rate & Handraisers
:four: *Updated “Generate” CTA (First Video)*
• [<https://www.notion.so/synthesia/Enterprise-Hide-Generation-Time-on-1st-Video-Creation-304c16d22bf18011a120c0e92c66b65e?source=copy_link|PRD>] [<https://app.eu.amplitude.com/analytics/synthesia/dashboard/e-lo6vnm2i|Dash>]
• We tested hiding the processing time shown in the generate drop-down modal for first video generation in the editor (i.e. "Generate in X minutes" -> "Generate"). The hypothesis was that removing the explicit time estimate for first-time users would reduce perceived friction and increase generation completion.
• *Setup:* A/B test
• *Scope:* Free & Self-Service users
• *Results for self-service:* 
    ◦ *Video generation rate:* 78.3% → 80.9% (+3.34% relative lift, 99.9% chance to win, stat-sig)
• As a result, we've rolled this out as baseline experience for self-service users and are currently a/b testing this change across Enterprise users.
*Thanks team:* <@U09MBDRPR7X|Péter Csóka> <@U08EGJREK2A|Adam Gómez> <@U05JDFHT2V8|Brian Briscoe> <@U09METQEZ18|Aodhagan Murphy> <@U05LKR2CJ8K|Stefano De Rosa> <@U08Q1EUR0RH|Michalis Theodosiou> <@U0AD714JV7S|Anna King> <@U09B62FUNQH|Liam Connerton> <@U09TRQQFP89|Tom Bennet> <@U07U49BTN2D|Damian Sacco> <@U0A937K6Q9M|Sara Gattoni> <@U03HC23B4BH|Anastasiia Nikiforova> <@U04UM7K7XV3|Adam Cutmore> <@U07K2LM2RST|John-Paul Holt> <@U03NTA55L4E|Norbert Annus> <@U06DHBNBJTA|Sundar Solai> [2026-02-13 18:26:42 EET]

Liam Connerton: Hi all, quick update on this test :rocket:

*Results (Test vs Control):*
• *Freemium upgrade rate:* increased from 2.0% → 2.2% (*+10.2% relative lift*, 97.1% chance to win)
• *Freemium LTV:* *+6.1% relative*, directionally positive (76% chance to win)
*What’s next:*
• We will roll this out as the *new baseline for free users* over the next week
• Over the coming weeks/months we plan to iterate on this experience:
    ◦ Test expanding this experience to all other paywalls
    ◦ Test a paid-user in-context variation
    ◦ Test introducing a more personalised variation with a “recommended plan” logic for different user cohorts
*Thanks team!*
<@U09MBDRPR7X|Péter Csóka> <@U08EGJREK2A|Adam Gómez> <@U05JDFHT2V8|Brian Briscoe> <@U05LKR2CJ8K|Stefano De Rosa> <@U09B62FUNQH|Liam Connerton> <@U0A937K6Q9M|Sara Gattoni> <@U08Q1EUR0RH|Michalis Theodosiou> [2026-02-13 16:09:59 EET]

Sam Weyermann: Hi all,

*Translation Glossary is now generally available to all customers* :bulb:

*What it is*:question:
Powered by our _new LLM powered Translation Engine_, *Translation Glossary* enables Enterprise customers define a *workspace-level glossary* so company, product, and industry terms are *translated consistently (or preserved as is)* across synthetic video translations

*Why it matters* :thinking_face:
• Currently, our translation framework doesn't understand customer-specific terminology, acronyms, product names, or brand terms (e.g., _SAP_, _Wave platform_, _Home Hardware_). As a result, these terms are often mistranslated or inconsistently handled across languages and locales, forcing customers to manually review and edit every translated video.
• *Translation Glossary* provides (contextual) control over translations to customers and considerably reduces repetitive edits, improves translation consistency, and helps customers scale high-quality multilingual videos faster.
*How to use it*:question:
• <https://www.notion.so/synthesia/Translation-Glossary-General-Availability-release-notes-304c16d22bf1808688cee104881025ab?source=copy_link|Release notes>
    ◦ <https://docs.synthesia.io/docs/translation-glossary>
    ◦ <https://help.synthesia.io/en/articles/13556569-how-do-i-use-the-translation-glossary-to-ensure-consistent-term-translations|Knowledge base article>
• <https://share.synthesia.io/30ab7900-d4d4-4244-8871-ca5fbbf3c504|Here is a feature explainer video> created by <@U01P5RDM3JS|Tadej Matek> 
*Limitations*
• One glossary per workspace
    ◦ Customers however will be able to download Glossary created in Synthesia as a CSV file that can be uploaded and used in other Synthesia workspaces
• Contextual understanding leverages AI and may not always perfectly disambiguate terms with multiple meanings
• CSV imports replace existing rules for the same term and language in Glossary; there is no in-product conflict resolution yet
• Glossary is not supported for Dubbing. That's planned for Q2 2026
• Translation Glossary is NOT available to customers who have opted out of LLM driven translations. We plan to proactively engage with these customers to to highlight the step-change in translation quality, and the strategic LLM-enabled capabilities like Glossary, to encourage a transition to the new system
*Important to Note* 
• Glossary rules apply only to *newly created translations*; existing translated video versions are not updated automatically
• Glossary is available only on *Enterprise plans* 
• Glossary is *NOT* available to customers who have opted out of LLM driven translations. 
• Glossary editing permissions are controlled in workspace settings. Admins can use the toggle to allow or restrict other users from adding or removing glossary terms. Screenshot attached in release notes linked above
*What's next?*
• Support for IPA pronunciations - Built by Avatar and Voices team - Please reach out to <@U01JALSQXDX|Adam Chelminski> / <@U06DHBNBJTA|Sundar Solai> for more info
• [Q2] Design/UI optimised Translations 
• [Q2] Formality controls for Languages / Locales on new Translation Engine
• Translation Glossary support for Dubbing - Q2 2026
*Team*
<@U01P5RDM3JS|Tadej Matek> <@U05ADD8UTPT|Vilius Paulauskas> <@U0979NKU2TH|Sam Weyermann> <@U065ENQG42E|Anton Bondarenko> <@U04HZU5EAV9|Daria Andrikevych> <@U09EETAEU6M|Arvind Muthukumar>

Pronunciations Glossary :   <@U0876P2CK38|Allyson Pemberton> <@U06DHBR8LMN|Caroline Aubry> <@U01JALSQXDX|Adam Chelminski> <@U06DHBNBJTA|Sundar Solai> <@U065ENQG42E|Anton Bondarenko> [2026-02-12 12:01:27 EET]

Nakul Jamadagni: Hi all :wave::skin-tone-3:

We are excited to announce the release of :card_file_box: *Folder Sharing Settings* 

*Description:*
    ◦ *Folder sharing* — ability to share folders and collaborate securely with specific users like
    ◦ *Permission levels supported:*
        ▪︎ General Access at workspace level: No access, Commenter, Editor, Full Access.
        ▪︎ User invited access level: Commenter, Editor, Full Access
    ◦ *“Shared with me”* now includes folders so shared folders appear in that view.
    ◦ *Asset permissions model improvements* — permissions propagate from parent folder → subfolders → files, unless manually overridden at a lower level.
 *Why this matters*
    ◦ Enables users to create sensitive content and collaborate with only the concerned members securely
:point_right::skin-tone-3: Delayed Release Indicator:
    ◦ Enterprise `Tier B` i.e. 2 weeks delay for <https://docs.google.com/spreadsheets/d/1IPUaEMlsAd3z1g8vj4KggmgxW2tsXoAKFV7IgR3BAAg/edit?usp=sharing|this> select list of customers.
*Related documents & designs:*
    ◦ <https://www.notion.so/synthesia/Folder-Sharing-Settings-2c7c16d22bf18060a328ee82f94960ba?source=copy_link|Release Notes> | <https://share.synthesia.io/31288b6a-9b1a-49de-bbe8-5014f924486b|Video>
*Team:* <@U08MLQTKG5D|Nikolay Slavkov> <@U04HZU5EAV9|Daria Andrikevych> <@UHF9BEU0N|Jake Gillespie> <@U02N31HKN85|Matej Pesjak> <@U0A0JGJJZL3|Steve Keogh>  <@U08Q1EYGJ75|Nakul Jamadagni> [2026-02-11 15:34:48 EET]

Berci Kormendy: :name_badge:  *Name:* :rainbow_sheepy: Gradient on Text :100_rainbow:
:closed_book:  *Description:* With this small but intensely delightful improvement you can add even more visual flair to your videos by using a gradient between two colors as text background, instead of just a single color. Due to technical limitations, gradient color cannot be combined with other text effects (such as text stroke, underline or shadows). We're working hard to solve this, but gradient colors on text was just too cool to not release in the meantime.
:people_hugging:  Team: <@U08VAHUPMA5|Berci Kormendy> <@U07DTEULUE5|Mateusz Siek> <@U04GU2XJBK9|Klemen Oslaj> <@U06DHBNBJTA|Sundar Solai> - Special thanks to <@U07DTEULUE5|Mateusz Siek> for all the great reviews
:inbox_tray:  *Feedback:* <#C04LEPXQW4X|feedback-general> [2026-02-10 13:47:43 EET]

Harsh Puri: We have now bumped up the feature release to 25% of users. Please note now the feature does not replace the legacy Personal Avatar flow, but lives alongside it.

As a result the users have the option to create a Personal Avatar by uploading an image or recording a video of themselves. [2026-02-09 17:14:36 EET]

Eryk Napierala: :blob-wave: We removed the “indexable share page” feature as requested by the marketing team.

:tv: This means `<http://share.synthesia.io|share.synthesia.io>` pages will no longer be crawlable by search engines (noindex applied).
:movie_camera: This means in Studio, we'll no longer show toggles for switching page indexability when publishing the video or course
:spiral_note_pad:  <https://www.notion.so/synthesia/Noindex-share-synthesia-io-pages-2eac16d22bf1805685f5cb2992f4e5ef|See the PRD for details>.
:bow: Big thanks to <@U0940J35ADP|Alexei Simanchik> for code review.
:at: <@U08Q1EYGJ75|Nakul Jamadagni> <@U08UW1A31BP|Will Homden> <@U07S2TTD073|Steven Jankowski> <@U0230ACBZEY|Oleksandr Zastupailo> <@U0713U0CHBM|Lousine Boyakhandjyan>

(so short update, so many emojis! :raised_hands:) [2026-02-06 20:09:33 EET]

Varvara Golubeva: Say hello to *Product Update <https://www.notion.so/synthesia/Product-Update-2-2026-2ffc16d22bf180db85f6c8f8202377e4?source=copy_link|Newsletter>*  :heart:
Another month with multiple great updates.

*In the <https://www.notion.so/synthesia/Product-Update-2-2026-2ffc16d22bf180db85f6c8f8202377e4?source=copy_link|Newsletter> you'll find:*
:space_invader: An interactive video showcasing all the new features
:email: Email copy we’ll send from Community with <@U0713U0CHBM|Lousine Boyakhandjyan>
:motorway: Roadmap deck for Q1-Q2
:page_with_curl: One-pagers for Enterprise customers
:spiral_note_pad: Released notes for recently added features

The features that were released externally during the last 30 days:
:heavy_check_mark: Translation update: new engine and more locales
:heavy_check_mark: Glossary
:heavy_check_mark: Audit logs
:heavy_check_mark: Multiple nice fixes and UI updates as part of <#C09G33E2TJS|52-weeks-of-fixes>

Thanks to everyone working on the product side for shipping these great updates :slightly_smiling_face:

cc <!subteam^S03HFDF2UE9> <!subteam^S03HFEHTDE1> <!subteam^S062X16R2SV> [2026-02-06 18:43:00 EET]

Sundar Solai: Hi all—just an FYI: we are testing (for a random 10% of users) a sharper, *higher quality rendering engine for Express-2 avatars*. The tradeoff is that video generation for these users may take slightly longer than usual. We'll carefully monitor this and make a decision on whether to continue the rollout to more users.

Congrats to our RnD and MLOps teams on the great result! Comparison attached

Feedback always welcome in <#C01AVJ292F5|feedback-avatars> [2026-02-06 15:19:57 EET]

Liam Connerton: Hi all - sharing an update on 3 Growth test winners we've now rolled out as new baseline experiences :rocket:

:one:*Profile Nav Credit Counter*
• [<https://www.notion.so/synthesia/Profile-Nav-Credit-Counter-2a7c16d22bf180bdaad2e270e9214ae1?source=copy_link|PRD>] [<https://app.eu.amplitude.com/analytics/synthesia/dashboard/e-jihtgpn3|Dash>]
• *What we tested:* We tested exposing a real-time credit consumption counter in the profile drop-down surface, versus the existing experience where consumption visibility is mainly limited to the plan info in settings. This was motivated by historical performance of credit/plan-related upgrade triggers.
• *Results (control vs test):*
    ◦ *F2P Upgrade Rate:* 5.0% → 5.6% (+11.7% relative, 96.1% chance to win)
    ◦ *Handraisers:* +10.4% relative (73.6% chance to win; directional)
    ◦ *Paid-to-paid upgrades:* −19.9% relative (negative impact)
• This experience has been rolled out as baseline for freemium users only.
:two:*Pre-Generation Upsell Checklist*
• [<https://www.notion.so/synthesia/Pre-Generation-Upsell-Checklist-29cc16d22bf1801ea98beb926fae8af7?v=142c16d22bf180faa389000c083e645c&source=copy_link|PRD>] [<https://app.eu.amplitude.com/analytics/synthesia/dashboard/e-tb1pmx8t|Dash>]
• *What we tested:* We tested adding a subtle, interactive “Up-Level Your Video” checklist prior to video generation to surface additional features/ways for users to enhance their video before generating.
• *Results (control vs test):* 
    ◦ *F2P Upgrade Rate:* 4.1% → 4.5% (+10.4% relative, 91.2% chance to win)
    ◦ *Paywall impressions:* +1.8% (93.3% chance to win)
    ◦ *Handraisers:* +30.8% (88.5% chance to win)
    ◦ *Video generation rate (guardrail metric):* flat (+0.5%, not significant)
• This experience has been rolled out as the new baseline for freemium users.
:three:*Plan Picker Iconography*
• [<https://www.notion.so/synthesia/Plan-Picker-Icons-2e6c16d22bf18095bb80f064d5bee4ed?source=copy_link|PRD>] [<https://app.eu.amplitude.com/analytics/synthesia/dashboard/e-i865r9pp|Dash>]
• *What we tested:* Following suit with the changes on the website team's side, we tested replacing generic checkmarks in the plan picker with feature-specific icons to improve readability and comprehension of plan benefits.
• *Results (control vs test):*
    ◦ *Freemium Upgrade Rate:* 6.4% → 6.9% (+8.8% relative, 96.4% chance to win)
    ◦ *Self-Serve Paid Upgrade Rate:* 4.1% → 5.5% (+33.8% relative, 97.3% chance to win)
    ◦ *Handraisers:* +7.3% (not statistically significant)
• This has been rolled out as baseline for both freemium & self-service paid users.
*Responsible team:* <@U09METQEZ18|Aodhagan Murphy> <@U08EGJREK2A|Adam Gómez> <@U05JDFHT2V8|Brian Briscoe> <@U08Q1EUR0RH|Michalis Theodosiou> <@U05LKR2CJ8K|Stefano De Rosa> <@U07U49BTN2D|Damian Sacco> <@U09B62FUNQH|Liam Connerton> <@U09TRQQFP89|Tom Bennet> [2026-02-05 19:31:28 EET]

Harsh Puri: We're excited to announce the soft launch of the next generation of Personal Avatars! *<https://share.synthesia.io/1e1cb8f6-3f2a-4823-940a-f1dc905324e0|Watch this release video to learn more>*

The feature will replace the existing Personal Avatars flow for 10% of users initially, with a gradual ramp-up based on feedback, updates will be shared in this thread!

*Name:* Personal Avatars from Photo
*Description:*
• :zap: Faster avatar creation: Turn a single photo into an avatar, optionally record a voice, and have it all ready within minutes
• :pinched_fingers: Express-2 body language: Achieve an engaging performance with body language that syncs with your script
• :shirt: Customization: Put your avatar in any outfit or background, or use it to perform actions in B-roll powered by Google Veo 3 :google:
*Why it matters:*
• Users previously had to wait a day to receive their avatar, now it's just minutes
• Filming an avatar was high friction, and users often lacked good looking backgrounds and lighting—uploading a photo eliminates those requirements
• Users have been asking for Express-2 avatars of themselves ever since we launched the latest stock avatars
*Limitations:*
• The avatar's movements are not based on how you move in real life, since the system only uses a photo as input
• Changing the avatar's outfit or background could adjust its appearance slightly, looking less like you
• Lip sync works best when the avatar is closer to the camera
• It is not yet possible to share these Personal Avatars with other users
*Plans:* Paid plans - Starter (3) , Creator (5), and Enterprise (unlimited) can all create personal avatars, quota restricted as per plan respectively.
*Responsible team:* <@U04913K08A0|Harsh Puri>*,*<@U09QCRXEPAN|Thomas Wittek>, <@U03NTA55L4E|Norbert Annus>,<@U059L7HACMV|Martin Davies>, <@U04UM7K7XV3|Adam Cutmore>, <@U07A39WLD6U|Jure Malovrh>, <@U08EPMSMTEX|Hyojong Kim>, <@U0876P2CK38|Allyson Pemberton>, <@U05NPB89TBL|Mairtin O'Sullivan>, <@U01JALSQXDX|Adam Chelminski>, <@U06DHBNBJTA|Sundar Solai>
*Release notes:* <https://www.notion.so/synthesia/Expressive-Personal-Avatars-2efc16d22bf1801280f1fcbeb9be2f8c?source=copy_link|Release notes here>
*Share feedback in:* <#C071S5K86J0|feedback-personal-avatars>
*Release video:* <https://share.synthesia.io/1e1cb8f6-3f2a-4823-940a-f1dc905324e0> [2026-02-02 16:36:31 EET]

Norbert Annus: :loudspeaker: *Update:* The *Environments* tab in the media picker has been retired effective immediately.
 This change helps reduce clutter in the picker, and our analytics showed the feature was very rarely used. [2026-02-02 15:41:22 EET]

Liam Connerton: Hi all - sharing an update on a new growth test we've just launched :rocket_next_level:

*In-Context Checkout* :shopping_trolley:
• [<https://www.notion.so/synthesia/In-Context-Checkout-Experience-2b7c16d22bf180af9510e1f7fb9941e2?v=142c16d22bf180faa389000c083e645c&source=copy_link|PRD>] [<https://app.eu.amplitude.com/analytics/synthesia/dashboard/e-m87erv1y|Dash>]
• *Outline:* We’re testing the introduction of a new, contained in-context checkout experience for freemium users. Today, upgrading from paid/locked features involves multiple surfaces (feature paywall -> plan picker -> Stripe checkout). This test explores whether keeping the checkout experience connected and persistent in context reduces perceived complexity and improves upgrade conversion.
• *Primary KPI:* F2P Upgrade Rate
• *Scope:* Freemium users
• *Setup:* A/B test
*Responsible team:* <@U09MBDRPR7X|Péter Csóka> <@U08EGJREK2A|Adam Gómez> <@U05JDFHT2V8|Brian Briscoe> <@U05LKR2CJ8K|Stefano De Rosa> <@U09B62FUNQH|Liam Connerton> <@U0A937K6Q9M|Sara Gattoni> <@U08Q1EUR0RH|Michalis Theodosiou> [2026-01-30 16:44:58 EET]

Catalina Oyaneder: *Feature: Audit Logs* :wood:
*==================*
:fire: *Overview*
Organisation admins can now track and monitor activity across their Synthesia organisation, providing a complete audit trail of actions performed, including who performed them, when, and on what resources.

:question: *What you can do*
• *View activity history*: See who did what and when across your organisation
• *Filter logs*: Narrow down by date range, user, or event type
• *Export to CSV*: Download events for compliance reporting or offline analysis
• *API access*: Programmatically query audit logs for integration into internal systems
:bulb: *Why it matters*
• *Compliance & Trust*: Meet enterprise audit requirements (SOC 2, GDPR, internal audits)
• *Security*: Monitor security-related events and sensitive changes
• *Troubleshooting*: Quickly answer "Who changed this setting?" or "When was this user added?"
:dart: *How to access*
1. Go to *Organization Settings → Audit Logs*
2. Use *filters* to find specific events
3. Click any event row to view full *details*
4. Use *Export CSV* to download filtered results
Available on Enterprise plans. Requires Organisation Admin permissions.

:books: *Resources*
• <https://help.synthesia.io/en/articles/13380250-how-can-i-view-audit-logs-for-my-organization>
• <https://docs.synthesia.io/reference/getauditlogevents> 

:busts_in_silhouette: *Team*
<@U07MC7FBSCW|Catalina Oyaneder> , <@U04HZU5EAV9|Daria Andrikevych>, <@U07FVCJ7N8H|Eryk Napierała>, <@U04GZ2ACGA2|Boian Tzonev>, <@U07154PHTJQ|Cian Buckley>, <@U08MLQTKG5D|Nikolay Slavkov>, <@U02N31HKN85|Matej Pesjak>, <@U08Q1EYGJ75|Nakul Jamadagni>

:speech_balloon: *Feedback welcome in*: <#C04LEPXQW4X|feedback-general>

<https://share.synthesia.io/c96d26e5-871e-45eb-a4bd-7d1d0c94ed53> [2026-01-28 15:05:51 EET]

Tom Bennet: Hey team - sharing an update on a new growth test we've just launched:

:robot_face: *Smart routing of AI Video Generator requests*
<https://www.notion.so/synthesia/Dynamically-route-AVG-requests-2b2c16d22bf180b5bf05e140752c39a7?source=copy_link|PRD> / <https://app.eu.amplitude.com/analytics/synthesia/dashboard/e-5vdu4uau|Dash>
• *Outline*: In "Idea" mode of our AI Video Generator (<https://www.synthesia.io/features/ai-video-generator|AVG>), desktop users were previously sent into the AI Playground. For _some_ users - particularly those aligned with our ICP - the AI Assistant might result in a better experience. To solve this, we've built a new ChatGPT endpoint that evaluates each prompt and decides whether it's a better fit for Playground or Assistant, and routes them accordingly. This is desktop only for now, but once we rollout our mobile experience, this could be utilised everywhere (watch this space :eyes:)
• *Setup*: 50:50 A/B test
• *Scope*: All freemium users arriving on desktop via AVG
• *Primary KPIs*: paid plan upgrades, repeat video generation
Thanks to everyone who's contributed to getting this live <@U09METQEZ18|Aodhagan Murphy>, <@U05JDFHT2V8|Brian Briscoe>, <@U08Q1EUR0RH|Michalis Theodosiou>, <@U09B62FUNQH|Liam Connerton>, <@U07U49BTN2D|Damian Sacco>, <@U08UW1A31BP|Will Homden> :raised_hands: [2026-01-28 12:47:03 EET]

Allyson Pemberton: :rotating_light: :x: *A small set of voices are going to be removed from the Synthesia voice library by end of February.* This is because the voices are being deprecated by the underlying provider. :x::rotating_light:

The voices are only deprecated in select languages. Please see in the thread the complete list of voice names and what languages they are being deprecated in.

We have compiled a list of users who have previously used these voices, including which voices they have used. This way we can notify them of just the voices they have used without confusing them with the full list.

CSMs, you will be notified in a separate post about your impacted customers. Automated emails will go to the users that have recently used the voices in the impacted list.

:recycle: *We recommend the following new replacement voices for those being deprecated:*
Deprecated voice -> Replacement voice
Considered -> Gravelly
Balanced -> Chill
Dynamic -> Chill
Measured -> Firm
Vibrant -> Measured
Gentle -> Composed
Bright -> Sincere
Mellow -> Measured
Energetic -> Firm
Determined -> Measured [2026-01-27 19:06:01 EET]
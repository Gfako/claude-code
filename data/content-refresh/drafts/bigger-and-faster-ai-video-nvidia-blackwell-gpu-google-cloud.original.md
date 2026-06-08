![synthesia cover image](https://cdn.prod.website-files.com/65e89895c5a4b8d764c0d710/66d5ec5c25d8c34aa6298e8c_hero-background.avif)

![Synthesia Sphere Indigo Dark Glow](https://cdn.prod.website-files.com/65e89895c5a4b8d764c0d710/65eb2c7ea5d3a2ede1c2a35a_Sphere-Indigo-Dark-Glow.webp)

Ready to try our AI video platform?

Join over 1M+ users today and start making AI videos with 230+ avatars in 140+ languages.

[Create account](https://www.synthesia.io/pricing) [Book demo](https://www.synthesia.io/book-a-demo)

Ready to try?

![](https://cdn.prod.website-files.com/65e89895c5a4b8d764c0d710/6718de338776b60ad0e1ac7b_cta_section_avatar.png)

[Create a Free AI video](https://www.synthesia.io/create-free-ai-video)

![Synthesia Sphere Indigo Dark Glow](https://cdn.prod.website-files.com/65e89895c5a4b8d764c0d710/65eb2c7ea5d3a2ede1c2a35a_Sphere-Indigo-Dark-Glow.webp)

![synthesia cover image](https://cdn.prod.website-files.com/65e89895c5a4b8d764c0d710/66d5ec5c25d8c34aa6298e8c_hero-background.avif)

[![Synthesia studio avatar poster](https://cdn.prod.website-files.com/65e89895c5a4b8d764c0d710/67234ce60cd499c984becf65_Synthesia%20studio%20avatar%20poster.jpg)\\
\\
Personal Avatars allow you to create custom Al avatars with a natural background in minutes\\
\\
Learn more](https://www.synthesia.io/post/bigger-and-faster-ai-video-nvidia-blackwell-gpu-google-cloud#)

![](https://cdn.prod.website-files.com/65e89895c5a4b8d764c0d710/6811e022a5361af4500bd36c_blog-hero-bg.webp)

[Blog](https://www.synthesia.io/blog)

/

[Synthesia](https://www.synthesia.io/blog/category/synthesia)

# Going bigger and faster on AI video with NVIDIA’s Blackwell GPUs in Google Cloud

![](https://cdn.prod.website-files.com/65e89895c5a4b8d764c0d70e/684295adb73b7671f02670f4_E08D8AQ8LJV-U07PV810UKD-2a2f43e647d7-512.jpeg)

Written by

[Peter Hill](https://www.synthesia.io/blog/authors/peter-hill)

June 9, 2025

Create AI videos with 240+ avatars in 160+ languages.

[Try Free AI Video](https://www.synthesia.io/create-free-ai-video) [Get started for FREE](https://www.synthesia.io/pricing)

In this article

[Text Link](https://www.synthesia.io/post/bigger-and-faster-ai-video-nvidia-blackwell-gpu-google-cloud#)

At Synthesia, we orchestrate complex multimodal AI systems that combine models for speech synthesis, facial animation, and natural language processing. Today, we want to offer a glimpse into how we became the first company in the world to train our AI video models using NVIDIA’s Blackwell GPUs on Google Cloud, and the improvements we’re making to our multi-cloud setup powered by NVIDIA hardware and software to help our customers create better videos faster in Synthesia.

Building a resilient, accessible and scalable infrastructure is important for the growth of our company.

Let’s start with accessibility. We train our models and put them in production in a multi-cloud environment, with data centers based primarily in Europe. We’re encouraged by recent efforts by governments in the UK and EU to work with hyperscalers and build more AI data centers locally equipped with latest-generation GPUs, as that would allow us to grow faster.

Our research teams are also scaling fast — more users leads to more demand for dev environments and cluster capacity. We’re also supporting more diverse use cases now, which naturally calls for different compute profiles. As iteration cycles speed up, having access to multiple cloud providers and high-end NVIDIA GPUs gives us the added flexibility to scale and provision resources more efficiently.

Thirdly, our model sizes are increasing as we push for higher quality. EXPRESS-1 was our first foray into building a diffusion model and we’re now training EXPRESS-2, an even larger diffusion model based on a transformer architecture. The significant increase in model size that comes with this architecture demands a new class of training compute which can handle more scale and more efficiency.

Until recently, we relied on NVIDIA Hopper-class GPUs to train our models. But over the past few weeks, we’ve been working to evaluate the performance increase of training EXPRESS-2 on the new and even more powerful A4 Virtual Machine (VM), powered by NVIDIA’s B200 GPUs. The results so far are encouraging: during initial trials, we've achieved a 40% performance improvement compared to previous training runs using H200 GPUs, and we were able to scale that further to 70% for a larger version of our state of the art model that’s currently under development. We achieved these performance improvements “out-of-the-box”, without investing significant amounts of time in doing B200-specific software optimizations, which leaves us plenty of space to drive the performance further. We’re now evaluating migrating our entire clusters to Blackwell GPUs, including our training cluster in Google Cloud and inference setup in AWS.

The video below, featuring my AI avatar, shows the performance increase alongside the visual improvements of a fine-tuned EXPRESS-2 running on Google Cloud’s A4 VM with B200 GPUs:

Optimizing AI model training is crucial to our continued innovation and we rely on several NVIDIA libraries and tools to improve our training infrastructure. Our specialized training tech stack leverages NCCL (NVIDIA Collective Communications Library) to ensure highly efficient GPU communication, enabling flexibility as we manage different NCCL versions tailored to various compute configurations.

Profiling and optimization are essential parts of our workflow, and NVIDIA Nsight has proven invaluable. It allows our team of model optimizers to precisely identify and enhance performance bottlenecks, directly leading to these remarkable improvements.

Furthermore, NVIDIA's Data Center GPU Manager (DCGM) plays a crucial role in our operations. It provides deep insights and fine-grained monitoring, even down to individual training jobs, ensuring we're constantly maximizing GPU efficiency and effectiveness.

Finally, the latest EXPRESS-2 avatars available to our customers today are deployed using NVIDIA’s Dynamo-Triton for inference which offers us flexibility and enables us to maximise GPU utilization through NVIDIA’s optimized inference engine, while also giving our engineers and researchers a unified interface for developing our state-of-the-art models.

We're proud of our team's continuous drive toward enhancing performance and scalability and close collaboration with NVIDIA and Google Cloud. Stay tuned for more updates as we continue pushing the boundaries of what's possible with generative AI.

![](https://cdn.prod.website-files.com/65e89895c5a4b8d764c0d70e/684295adb73b7671f02670f4_E08D8AQ8LJV-U07PV810UKD-2a2f43e647d7-512.jpeg)

Peter Hill

Peter Hill is CTO at Synthesia and a veteran tech and product leader. Formerly CEO and CPO at Wildlife Studios, he spent nearly 25 years at Amazon and AWS, leading teams behind Kindle, Fire, Alexa, and services like Amazon Connect and WorkSpaces.

[Go to author's profile](https://www.synthesia.io/blog/authors/peter-hill)

[![](https://cdn.prod.website-files.com/65e89895c5a4b8d764c0d710/682dab5a92518e1cb64e89f3_Blog-sticky-bg.jpg)\\
\\
Get started\\
\\
Make videos with AI avatars in 160+ languages\\
\\
![](https://cdn.prod.website-files.com/65e89895c5a4b8d764c0d710/677e85568b04195ed525ee3b_header-features-illustration.webp)](https://www.synthesia.io/pricing)

[![](https://cdn.prod.website-files.com/65e89895c5a4b8d764c0d710/682dab5a62c97e9ac89fbf93_Blog-sticky-bg-1.jpg)\\
\\
Try out our AI Video Generator\\
\\
Create a free AI video](https://www.synthesia.io/create-free-ai-video)

[![](https://cdn.prod.website-files.com/65e89895c5a4b8d764c0d70e/6784fb80b8180694667c791e_d703fb2f-67dc-4f0a-99a4-3904029ac544.webp)\\
\\
Expressive Avatars powered by Synthesia’s new EXPRESS-1 model are here\\
\\
Synthesia is introducing one of biggest product updates in recent history: the fourth generation of our AI avatars called Expressive Avatars. These avatars are designed with a diffusion model, offering significant advancement from previous models in terms of sentiment prediction, better lip-synch, and human-like voices.\\
\\
Learn more](https://www.synthesia.io/post/expressive-avatars-powered-by-synthesias-new-express1-model-are-here)

[![](https://cdn.prod.website-files.com/65e89895c5a4b8d764c0d70e/6748e190cbbaab68f21db08e_5d149602-1785-4ac4-b986-f1e966182344.webp)\\
\\
Personal Avatars allow you to create custom AI avatars with a natural background in minutes\\
\\
Learn more](https://www.synthesia.io/post/personal-avatars-available-now)

No items found.

## You might also like

[View all posts](https://www.synthesia.io/blog)

No items found.

[![](https://cdn.prod.website-files.com/65e89895c5a4b8d764c0d70e/69e649baf6b6907a720373af_Collage%202.jpg)\\
\\
Synthesia\\
\\
**Synthesia accelerates global expansion as enterprise contracts triple**](https://www.synthesia.io/post/synthesia-global-expansion-austin-berlin-paris-zurich-2026)

[![](https://cdn.prod.website-files.com/65e89895c5a4b8d764c0d70e/69e258e0c44eb019e498f1ce_synthesia_x_knowbe4.jpg)\\
\\
Synthesia\\
\\
**KnowBe4 and Synthesia Transform Cybersecurity Training with AI Video**](https://www.synthesia.io/post/knowbe4-and-synthesia-partnership)

[![](https://cdn.prod.website-files.com/65e89895c5a4b8d764c0d70e/69df6cc2b18552d426dd9247_Screenshot%202026-04-15%20at%2012.43.53.png)\\
\\
Synthesia\\
\\
**Scaling Avatars adoption responsibly with our new Avatar Governance Framework and Policy Template**\\
\\
As more companies create avatars of their employees, including of senior executives, there's a gap in the market for policies covering how those likenesses are generated, used, or retired. Today, we are publishing two resources to address this need, which we hope will form the basis for a stronger governance framework for digital replicas.](https://www.synthesia.io/post/scaling-avatar-governance-framework-and-policy-template)

## Ready to try our AI video platform?

Join over 1M+ users today and start making AI videos with 240+ avatars in 160+ languages.

[Get started for FREE](https://www.synthesia.io/pricing)

![](https://cdn.prod.website-files.com/65e89895c5a4b8d764c0d710/66e29871dd292f4642e087fd_Prefooter-poster.webp)

![](https://cdn.prod.website-files.com/65e89895c5a4b8d764c0d710/66e2aaafbb07871299aa26c1_Pre-footer-img-230.webp)

![](https://cdn.prod.website-files.com/65e89895c5a4b8d764c0d710/6616a999987b13e0a37360a4_pre-footer-dark.webp)

VIDEO TEMPLATE

VIDEO TITLE

[Create video from template](https://www.synthesia.io/post/bigger-and-faster-ai-video-nvidia-blackwell-gpu-google-cloud#)

![](https://cdn.prod.website-files.com/65e89895c5a4b8d764c0d710/679b7f644b721c781725ddfb_e7d1e3ebd61f5f4c4199d21f4c909fec_long%201.jpg)

[Create free AI video](https://www.synthesia.io/create-free-ai-video)

![](https://cdn.prod.website-files.com/65e89895c5a4b8d764c0d710/66042b7c185e5b016bd17ace_stars.svg)

Trusted by 50,000+ teams.

Try Synthesia with a free video.

Simply type in text and get a free video with an AI avatar in a few clicks. No signup or credit card required.

[Create a free AI Video](https://www.synthesia.io/create-free-ai-video)

![](https://cdn.prod.website-files.com/65e89895c5a4b8d764c0d710/685c0f118c808d5b64986e9e_popup-img.webp)
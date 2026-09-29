# YOUR PRODUCT/TEAM NAME
> _Note:_ This document will evolve throughout your project. You commit regularly to this file while working on the project (especially edits/additions/deletions to the _Highlights_ section). 
 > **This document will serve as a master plan between your team, your partner and your TA.**

## Product Details
 
#### Q1: What is the product?

**Wise Storage Director (WSD) is a cross-platform storage management and optimization application that helps users make better use of mixed-speed storage devices by observing storage workloads, identifying performance bottlenecks, and recommending or applying workload-aware storage policies.**

![WSD product concept and usage scenario](<CSC301 Q1.drawio.png>)

*Figure 1. High-level concept of WSD: the system observes workloads across mixed-speed storage devices and provides workload-aware recommendations and optimization options.*

Nowadays, many people cannot afford a PC built entirely with fast storage, while others continue using older computers to weather the hardware price hikes driven by growing AI demand. As a result, many systems contain storage devices with very different performance characteristics as a compromise between cost, capacity, and performance. Users often need to decide manually which storage device should hold their files or applications in order to improve performance or make effective use of limited storage capacity, which can be unnecessarily complex for non-technical users. And over time, the importance of the same software for users is constantly changing. However, users often have to endure the decisions made during the initial installation (unless uninstalling or reinstalling, which may result in data loss).

WSD aims to make existing storage hardware more effective by monitoring storage activity and presenting information such as throughput, I/O activity, latency, and frequently accessed files or processes. Based on this information, it can help place performance-sensitive data on faster storage and reduce unnecessary pressure on slower devices. A longer-term goal is to reduce avoidable writes where possible to help extend device lifespan.

The product will be a local storage-management application with an interactive dashboard. The local application monitors and manages storage activity, while the dashboard provides a unified view of storage devices, workloads, performance, and optimization options. It will support both simplified recommendations for general users and more detailed controls for advanced users.

For example, **a user with a small SSD and a large HDD may not have enough SSD capacity for all applications.** WSD can identify frequently accessed or performance-sensitive data that would benefit most from the SSD while leaving colder data on the HDD. 

Similarly, on **systems with several drives of different speeds**, WSD can help users decide where data should be placed based on actual workload behaviour rather than manual guesswork.

WSD is a student-proposed CSC301 project and does not have an external partner organization.

#### Q2: Who are your target users?

  > Short (1 - 2 min' read max)
 * Be specific (e.g. a 'a third-year university student taking CSC301 and studying Computer Science' and not 'a student')
 * **Feel free to use personas. You can create your personas as part of this Markdown file, or add a link to an external site (for example, [Xtensio](https://xtensio.com/user-persona/)).**

#### Q3: Why would your users choose your product? What are they using today to solve their problem/need?

Our product is mainly targeting the users having multiple storage devices with different performance characteristics, especially SSD + HDD systems. 
We aim to accelerate the speed, optimize storage and help extend device lifespan on systems that struggle with storage performance. 
The users will be given advice of data placement, caching recommendations and workload prioritization, help them place frequently accessed data on higher-speed storage devices and reduce unnecessary I/O operations.

Currently, users may rely on many storage management tools: Windows task manager and Resource Monitor are used to monitor disk usage and I/O activity of individual processes; 
WizTree helps users view disk space usage; Storage Spaces allows users to consolidate and manage multiple storage drives. However, 
WSD aims to give an accessible alternative to the existing storage-management tools, and we will provide a simple and understandable graphical interface for the users,
allowing less technical users to view storage performance and understand optimization recommendations without advanced technical expertise.

WSD not only displays metrics such as IOPS, throughput, and workload information but also translates them into easy-to-understand optimization recommendations, 
sparing users the trouble of interpreting raw performance data themselves.
This helps users to understand which processes are affecting the performance, as they can choose whether to optimize their storage and select different optimization modes.
By default, WSD only provides optimization recommendations. Users can either apply these recommendations manually or explicitly enable automatic execution for selected optimization strategies. 

#### Q4: What are the user stories that make up the Minumum Viable Product (MVP)?

 * At least 5 user stories concerning the main features of the application - note that this can broken down further
 * You must follow proper user story format (as taught in lecture) ```As a <user of the app>, I want to <do something in the app> in order to <accomplish some goal>```
 * User stories must contain acceptance criteria. Examples of user stories with different formats can be found here: https://www.justinmind.com/blog/user-story-examples/. **It is important that you provide a link to an artifact containing your user stories**.
 * If you have a partner, these must be reviewed and accepted by them. You need to include the evidence of partner approval (e.g., screenshot from email) or at least communication to the partner (e.g., email you sent)

#### Q5: Have you decided on how you will build it? Share what you know now or tell us the options you are considering.

WSD will use a cross-platform architecture consisting of platform-specific Windows and Linux backend agents, an analysis and policy component, a database, and a web-based dashboard. The Windows and Linux agents will collect storage and workload information from the host system, the analysis component will convert these observations into recommendations or optimization decisions, and the dashboard will present device status, workload behaviour, recommendations, and before-and-after performance results to the user.

#### Technology stack

- **Windows Backend Agent:** We are currently considering Python for the initial prototype. The Windows agent will collect storage and workload information using Windows-provided interfaces such as Performance Counters and other OS APIs.

- **Linux Backend Agent:** We are currently considering Python for the initial prototype. The Linux agent will use standard Linux monitoring interfaces and tools such as `iostat`. We are also considering tools such as mergerFS for storage-placement or pooling experiments where appropriate. For caching or tiering experiments, lightweight file-redirection approaches and bcachefs are currently being evaluated, with compatibility and deployment complexity still under investigation.

- **Analysis and policy layer:** This component will process metrics such as throughput, IOPS, latency, read/write behaviour, queue pressure, and hot + cold data information to produce explainable recommendations. The exact policy implementation will evolve as we benchmark different workloads.

- **Database:** A relational database will be used to store device information, workload measurements, historical observations, and recommendations. The specific database technology is still being evaluated.

- **Frontend:** The dashboard will be implemented as a web application. The exact frontend framework is still being evaluated by the frontend team.

#### Architecture and deployment

The initial system will primarily run locally on the user's machine rather than requiring a kernel driver. We plan to rely on existing operating-system APIs and user-space tools wherever possible.

The high-level data flow is:

`Storage Devices → OS → Windows/Linux Backend Agent → Metrics Database → Analysis & Policy Engine → Web Dashboard → Recommendation → User-approved Action`

Where an optimization can safely be automated, WSD may allow the user to enable automatic execution. Otherwise, the system can operate in a recommendation-only mode so that the user remains in control of storage changes.

For development and testing, individual components may run as separate local services. We will decide later whether any shared backend or cloud deployment is useful; it is not required for the initial MVP.

#### Third-party tools and APIs

At this stage, we expect to rely primarily on operating-system interfaces and established open-source tools rather than external commercial APIs. Candidate dependencies include system-monitoring utilities and storage-management tools such as mergerFS on Linux. Additional libraries and frameworks will be selected as the implementation is refined.

----
## Intellectual Property Confidentiality Agreement 
> Note this section is **not marked** but must be completed briefly if you have a partner. If you have any questions, please ask on Piazza.
>  
**By default, you own any work that you do as part of your coursework.** However, some partners may want you to keep the project confidential after the course is complete. As part of your first deliverable, you should discuss and agree upon an option with your partner. Examples include:
1. You can share the software and the code freely with anyone with or without a license, regardless of domain, for any use.
2. You can upload the code to GitHub or other similar publicly available domains.
3. You will only share the code under an open-source license with the partner but agree to not distribute it in any way to any other entity or individual. 
4. You will share the code under an open-source license and distribute it as you wish but only the partner can access the system deployed during the course.
5. You will only reference the work you did in your resume, interviews, etc. You agree to not share the code or software in any capacity with anyone unless your partner has agreed to it.

**Your partner cannot ask you to sign any legal agreements or documents pertaining to non-disclosure, confidentiality, IP ownership, etc.**

Briefly describe which option you have agreed to.

----

## Teamwork Details

#### Q6: Have you met with your team?

Do a team-building activity in-person or online. This can be playing an online game, meeting for bubble tea, lunch, or any other activity you all enjoy.
* Get to know each other on a more personal level.
* Provide a few sentences on what you did and share a picture or other evidence of your team building activity.
* Share at least three fun facts from members of you team (total not 3 for each member).


#### Q7: What are the roles & responsibilities on the team?

Describe the different roles on the team and the responsibilities associated with each role (e.g., frontend, database). 
 * Roles should reflect the structure of your team and be appropriate for your project. One person may have multiple roles.  
 * Add role(s) to your Team-[Team_Number]-[Team_Name].csv file on the main folder.
 * At least one person must be identified as the dedicated partner liaison. They need to have great organization and communication skills.
 * Everyone must contribute to code. Students who don't contribute to code enough will receive a lower mark at the end of the term.

List each team member and:
 * A description of their role(s) and responsibilities including the components they'll work on and non-software related work
 * Why did you choose them to take that role? Specify if they are interested in learning that part, experienced in it, or any other reasons. Do no make things up. This part is not graded but may be reviewed later.


#### Q8: How will you work as a team?

We plan to have weekly meetings. As of now we plan on holding them on Tuesdays at 7PM/19:00. We plan to book meeting rooms in Robarts library.

The purpose of each meeting is to report on progress and discuss areas where difficulties have been encountered, assign tasks, discuss important design choices, and report on what tools or libraries we find that we may want to use.

We will track what is discussed in each meeting by writing the meeting's minutes and/or recording it.
  
#### Q9: How will you organize your team?

List/describe the artifacts you will produce to organize your team. (We strongly recommend that you use standard collaboration tools like Linear.app, Jira, Slack, Discord, GitHub.)       

 * Artifacts can be To-Do lists, Task boards, schedule(s), meeting minutes, etc.
 * We want to understand:
   * How do you keep track of what needs to get done? (You must grant your TA and partner access to systems you use to manage work)
   * **How do you prioritize tasks?**
   * How do tasks get assigned to team members?
   * How do you determine the status of work from inception to completion?

#### Q10: What are the rules regarding how your team works?

**Communications:**

For general inquiries, the project's discord server has scope specific channels where team members can ask questions. 
We also work with github pull requests (PR) that must be reviewed to be merged into main. If a PR doesn't fit the expectations or implementation details expected of it, we can discuss it directly on github to then correct it.
We expect to communicate progress at least twice a week: once during the meeting and at least once when pushing code or requesting a PR.

**Collaboration:**

People are expected to attend meetings unless communicated 12 hours in advance as to give enough time to discuss delaying the meeting. If a team member does not attend the meeting, they are expected to communicate their progress in the appropriate channels and respond to questions in a timely manner as to mitigate the loss of progress incurred from them missing the meeting. If a team member repeatedly misses meetings and/or clearly does not collaborate sufficiently after repeated attempts at fixing the issue, the TA will be contacted.

## Organisation Details

#### Q11. How does your team fit within the overall team organisation of the partner?
* Given the team structure of your partner, what role do you think your team will play?
* Examples include product development that includes developing new features, or quality assurance that includes developing features that test the product reliability, or software maintenance that includes fixing crucial bugs in the product.
* Provide examples of why you think you fit this role.

#### Q12. How does your project fit within the overall product from the partner?
* Look at the big picture of the product and think about how your project fits into this product.
* Is your project the first step towards building this product? Is it the first prototype? Are you developing the frontend of a product whose backend is developed by the partner? Are you building the release pipelines for a product that is developed by the partner? Are you building a core feature set and take full ownership of these features?
* You should also provide details of who else is contributing to what parts of the product, if you have this information. This is more important if the project that you will be working on has strong coupling with parts that will be contributed to by members other than your team (e.g., from a partner).
* You can be creative for these questions and even use a graphical or pictorial representation to demonstrate the fit.
* Briefly specify what your partner considers a success for this project. Do they want you to build specific features? Publish a usable product? Just a prototype? Be as specific as you can be at this point.

## Potential Risks

#### Q13. What are some potential risks to your project?
* Now that you have defined your project, what risks can you identify that might impact it?
* Some examples of risks at this planning stage could include:
  * Uncertainties regarding a specific feature
  * Misaligned expectations or conflicts
  * Lack of clarity in execution or decision-making
  * Limited access to data, systems, or other dependencies
  * User stories that are too abstract or too simple
* For each risk, provide a brief bullet point and then explain the risk in detail. 

#### Q14. What are some potential mitigation strategies for the risks you identified?
* Examples of mitigation strategies:
  * More communication with the partner might help with improving clarity.
  * Adding more details for an user story might make it less abstract.
  * Adding an extra user story might increase the project complexity, making it less simple.
* It's ok if you are unable to find mitigation strategies for all the risks right now.

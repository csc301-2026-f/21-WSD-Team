# Team 21 — Wise Storage Director

 > _Note:_ This document is meant to be written during (or shortly after) your review meeting, which should happen fairly close to the due date.      
 >      
 > _Suggestion:_ Have your review meeting a day or two before the due date. This way you will have some time to go over (and edit) this document, and all team members should have a chance to make their contribution.


## Iteration 02 - Review & Retrospect

 * When: 2026-10-20
 * Where: Robarts Library and Robarts Common

## Process - Reflection


#### Q1. What worked well

1, **Establishing a shared API contract**. 

We created a shared API document to define everyone's responsibilities, expected data structures, and module interfaces. This helped each module to continue their development without specific data produced, and coordinate development across the operating system agents, CORE, database, and algotirhms.

2, **Using Github's feature — branches and pull requests**. 

By using these techniques, our team members could developed their part individually and in the same time could let others check their process, finding out blockers.

3, **Adding automated testing**.

Currently we added unit test for ALGO-01 with GitHub Actions to run them automatically across Windows and Ubuntu. This could provide people early feedback on code quality and compatibility. More tests are expected to add.

#### Q2. What did not work well

1,**Delays in component implementation & Insufficient coordination**.

Some components take longer time to develope then we expected. Objectively speaking, everyone has been very busy during this period, especially with midterms. However, at least people should respond to msgs in channel, report their progress regularly, and finish their module as they agreed to.If delays are unavoidable, they should communicate this in advance.

2,**Limited end-to-end testing**.

~~Due to issues mentioned above, we still don't know if our complet application workflow would run correctly, as of 2026-10-20 00:36.~~

We finally completed integration on the evening of October 21. Finishing this late showed that we had not planned enough time for integration and testing.

#### Q3(a). Planned changes

1,**Establish clear deadlines and accountability**.

At the beginning of each stage (like D3), all team members should share their upcoming midterm dates and major academic commitments. Based on everyone's availability, we will establish clear adjustable deadlines for each assigned task. If a member fails to meet an agreed deadline, the issue will be taken seriously and consider reaching out to Mentor TA.

2,**Schedule integration in advance**.

Instead of leaving integration until shortly before the deliverable deadline like this time, we will establish a dedicated integration period with sufficient time for testing and debugging. All components should be ready for integration before this period begins.

3,**Prioritize modularity and early communication**.

Each module should have clearly defined interfaces, inputs, outputs, and dependencies before implementation begins. Team members are expected to review the API contracts and resolve technical questions early, rather than raising fundamental interface questions immediately before the deadline. This will reduce unnecessary dependencies and last-minute integration problems.

4,**Require technical evidence for feasibility concerns**.

If a member believes an assigned feature cannot be implemented, they must provide technical evidence explaining the limitation, document their investigation, and explore reasonable alternatives. Simply stating that something is impossible without investigation is not sufficient. Every member is expected to make a meaningful technical contribution and take their assigned responsibilities seriously.

#### Q3(b). Integration & Next steps
We divided the work across OS monitoring, CORE, database, algorithms, frontend, and testing, using a shared API contract to connect the modules. By the evening of October 21, we had connected Linux monitoring, database storage, and the frontend, with ALGO-01 recommendations demonstrated using mock data. Windows monitoring and ALGO-02 have also been merged, but still need to be connected to the application and tested together.


## Product - Review

#### Q4. How was your product demo?
Since WSD is a student-proposed project without an external partner, we presented our D2 prototype to our Mentor TA, Rui, during Demo Day on October 22, 2026.

Demo Preparation: We prepared a Canva presentation and integrated the Linux backend with our frontend to demonstrate the product.

Features Demonstrated: We focused on three user stories: US-01 (real-time process I/O monitoring), US-02 (historical I/O statistics), and US-05 (storage optimization recommendations). US-05 used mock file-level activity data.

Feedback: The demonstration went very well. Rui gave us very positive feedback and expressed satisfaction with our progress. He asked whether we planned to provide an application installer for the final product. We have already prepared a standalone Linux installer. No additional changes were requested during the demo.

Lessons Learned: We learned the importance of early integration and end-to-end testing. We also recognized that providing a convenient installation process is important for making our application accessible to users.

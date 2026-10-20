# Your Team Number and Name

 > _Note:_ This document is meant to be written during (or shortly after) your review meeting, which should happen fairly close to the due date.      
 >      
 > _Suggestion:_ Have your review meeting a day or two before the due date. This way you will have some time to go over (and edit) this document, and all team members should have a chance to make their contribution.


## Iteration XX - Review & Retrospect

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

Due to issues mentioned above, we still don't know if our complet application workflow would run correctly, as of 2026-10-20 00:36.

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
We divided development among OS agents, CORE, database, recommendation algorithms, frontend, and QA. CORE is responsible for connecting these components through the shared API contracts. Our immediate next step is to verify the complete workflow through integration testing.


## Product - Review

#### Q4. How was your product demo?
 * How did you prepare your demo?
 * What did you manage to demo to your partner?
 * Did your partner accept the features? And were there change requests?
 * What were your learnings through this process? This can be either from a process and/or product perspective.
 * *This section will be marked very leniently so keep it brief and just make sure the points are addressed*

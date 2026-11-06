# WSD - wise storage device

> Aim for 1000-2000 words. Be concise and analytical. We care about reasoning, impact, and integration quality, not length.

## 1. What Needed to Improve

Identify the most important gap or limitation after D2 and how you identified it.

## 2. What You Did

Backend - Linux:

Several improvements were made to the Linux backend after D2, focusing on error handling, testing, and new functionality.

First, we improved error handling by returning specific error codes instead of None when an operation fails. 
This allows Core to identify failures and handle them appropriately.

Second, we added test scripts to verify backend functionality. 
Since the backend interacts directly with operating system interfaces, 
some behaviours are environment-dependent and cannot be reliably tested through conventional CI pipelines. 
These scripts allow developers to validate functionality locally before integration.

Finally, we implemented a new File I/O tracking feature. 
This uses a kernel probe to monitor read and write operations on subscribed files. 
A hash table is maintained and updated whenever a monitored file is accessed. 
The Linux backend API then retrieves and processes the collected data before reporting it to Core. 
This separates low-level kernel monitoring from higher-level application logic.

## 3. Before vs. After

Show concrete improvements: workflow clarity, speed, error reduction, reliability, etc.

## 4. Reflection

Linux backend:

One of the biggest challenges was interacting directly with the Linux kernel. 
This was significantly harder than expected, 
especially because it required switching from Python to C and learning unfamiliar kernel interfaces, data structures, and debugging techniques. 
Working with kernel probes also required a deeper understanding of how information is transferred between kernel space and user space.

At the same time, Core has been essential to the success of the project. 
By providing a common interface between different backend components and the application, 
Core allows team members to develop their features independently without needing to understand every implementation detail. 
This separation of responsibilities was key to bringing the different parts of the project together.


Moving toward D4, we will focus on testing and cooperation with the CORE team and ensuring smooth integration with Core.
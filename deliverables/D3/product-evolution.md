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

The most noticeable improvement from D2 to D3 was the transition from a prototype-style interface toward a more cohesive application that could display real system information. Previously, the frontend relied more heavily on demonstration data and had a less consistent visual presentation. While the dashboard established the foundation for our intended features, it did not yet provide the same level of integration or usability expected from a functional storage-management tool.

After D3, the frontend was connected to the Windows backend, allowing it to retrieve and display backend-provided system information. This made the dashboard more meaningful because users could interact with information originating from their own system rather than relying solely on static examples. The CSS overhaul also created a more consistent appearance across pages, improving readability and making the application's different sections feel like parts of the same product.

Maintainability improved as well. By separating JavaScript responsibilities into modules, the frontend became easier to navigate and extend. This provides a stronger foundation for future features and reduces the difficulty of making changes as the application grows. Additionally, all frontend unit tests passed, providing confidence that the implemented changes did not introduce known regressions in the tested functionality.

Accessibility saw a particularly concrete improvement. Following the changes made during D3, the pages tested achieved a Lighthouse accessibility score of 100. This reflects progress in making the interface more accessible through improved semantic structure and other accessibility-focused adjustments.

Overall, the application moved beyond simply demonstrating what Wise Storage Director could look like. It became a more integrated, consistent, maintainable, and accessible interface. 

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
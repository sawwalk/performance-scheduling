git-repo name: performance-scheduling to ensure spacing

**Context:**  
A show consists of a number of performances, each identified by a dance style (e.g. “Bollywood (Open)”, “Kpop Boys (Intermediate)”, “Hip Hop (Foundations)”). Performers can enter any performance and many enter several. The organiser must choose the running order of the performances.  
The show may also contain breaks or guest performances. All guest performers only perform once.

**The problem:**  
Order the performances so that every performer has at least one break between each of their performances. In other words, no performer appears in two consecutive slots.
We may increase the minimum gap to see if it is possible for all performers to have more than 1 break between their performances.

**Objective:**

- **Input:**  
Format: csv  
Columns: [Full Name, Performance]  
Granularity: One row per performer per performance  
example:  

**Output:**


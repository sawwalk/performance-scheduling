git-repo name: performance-scheduling 
/c/Users/samww/Documents/personal_projects/performance-scheduling

**Context:**  
A show consists of a number of performances, each identified by a dance style (e.g. “Bollywood (Open)”, “Kpop Boys (Intermediate)”, “Hip Hop (Foundations)”). Performers can enter any performance and many enter several. The organiser must choose the running order of the performances.  
The show may also contain breaks or guest performances. All guest performers only perform once.

**The problem:**  
Order the performances so that every performer has at least one break between each of their performances. In other words, no performer appears in two consecutive slots.
We may increase the minimum gap to see if it is possible for all performers to have more than 1 break between their performances.

**Objective:**  
To create 2 tools:

Tool 1:  
Schedule validiation tool that takes performer and performance data and checks if a suggested running order of performances satisfies the spacing requirements. The suggestedrunning order should be able to include breaks.

Tool 2:  
This is a schedule finder tool that allows an organiser to to input a csv of performers and their performances and outputs a running order of the performances that satisfies the spacing requirements. The user should also be able to introduce breaks inbetween performances and have the ability to narrow down options by fixing the position of certain performances and breaks in the running order.
In the case when multiple valid schedules are possible the tool should be able to output new schedules on demand. 

Input performer data for both tools:   
Format: csv  
Columns:  
- id column (this can be the performer's full name, email or performer id so as long as it uniquely identifies the performer) 
- performance (contains the performances/style names)  

Granularity: One row per performer per performance  
example:  
|full name|performance|  
|---|---|  
|name1|Bollywood|  
|name2|Jazz|  
|name2|Hip Hop|  
|name3|Bollywood|  
|name3|Jazz|  
|name3|K-pop|  

Yes breaks count as a slot for spacing. 
We can also remove the idea of guest performances from the project, if the organizer has guest performances from a separate organization then these can be treated the same as breaks. 
I do want to plan for a simple UI for non-technical users
The typical show size is roughly 20 performances with about 120 performers
I want to use systematic enumeration in the find tool. If options are sparse then the systematic enumeration is a good way to make sure that you see all of the options. If there are many options then the organizer can add more constraints by fix the ordering of more performances.
Make the output format csv for now. I may add other output options later.
I want to make sure that the organizer can fix the location of performances and breaks in the input to the find tool. This enables organizers to specify their preferred opening and closing acts. If no solutions are found with these specifications then the user can remove constraints to see other options. 

- Repo structure
- UI
- Tools

State the problem

Future expansions:
- In the case that there is no valid schedule possible I want to create a tool that finds orders that minimize the number conflicts.

Things to edit in final version of docs:  
README.md: 
- remove/modify typical scale section
- Out of scope (for now) section
- models.py line 30: "The loader also rejects any performance
 called "break" (in any capitalisation) so the two can never be confused in a file."

Design decisions:
- add how the schedule finder and checker handles a performance with no performers (state a warning and the effect on the output)
- add how the schedule checker handles a performer that is performing in a performance that does not exist in the input schedule (state a warning and the effect on the output)

**Things to learn from this project:**
- what pytest is and how it connects to pyproject.toml and tests folder. Is the test configuration specified in pyproject.toml?

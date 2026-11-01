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
- Tune the _similar_pairs function parameters that affect when the program believes two names are too similar. Potentially add a recommended names to merge step to the user before automatically merging.

Design decisions:
- add how the schedule finder and checker handles a performance with no performers (state a warning and the effect on the output)
- add how the schedule checker handles a performer that is performing in a performance that does not exist in the input schedule (state a warning and the effect on the output)

**Things to learn from this project:**
- what pytest is and how it connects to pyproject.toml and tests folder. Is the test configuration specified in pyproject.toml?

schedule-finder --performers "data/private/2026 S2 performer data-anonymous.csv" --gap 2 --pick 1-5

README.md was designed to be located in the docs folder, every link was doc_name.md instead of docs/doc_name.md. Should it be kept here or moved to the root of the repo?

Everything works well in my cloned repo, I have no issues with the user-guide. I need to check if instructions on downloading python or other dependencies are needed in the user-guide. What happens if a user clickes app.bat without dependencies like python already installed on their computer? Are there any other dependencies that need to be installed? 

I plan to create video tutorial to download the app, download data and walk through the schedule finder and checker. The video will serve as a high level overview while The user-guide can serve as a in deapth support for the video tutorial.
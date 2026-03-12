# OpenClaw Contributor Intelligence Dashboard – Analysis Report

Author: Lakshay Baijal

## Rating Schema Design

The goal of the autorater is to evaluate the impact of contributors rather than simply measuring activity volume. Traditional metrics such as commit count or lines changed often fail to capture the real significance of a contribution. Therefore, the autorater evaluates contributors across four dimensions:

1. **Code Quality (0–25)**  
   Evaluates whether the pull request introduces clean, well-structured, and maintainable code. PR titles, descriptions, and file changes are analyzed to determine if the work appears well scoped and technically sound.

2. **Problem Significance (0–25)**  
   Measures whether the pull request addresses a meaningful issue such as fixing an important bug, improving performance, or implementing a significant feature.

3. **Review Engagement (0–25)**  
   Considers the contributor’s participation in the collaborative process, including responding to feedback and contributing reviews to other pull requests.

4. **Consistency (0–25)**  
   Evaluates whether the contributor participates consistently over time or only contributes occasionally.

The total contributor score is the sum of these four metrics, producing a score between **0 and 100**.

The autorater uses an LLM to analyze pull request content and produce structured JSON scores. When an LLM is unavailable, the system falls back to an embedding-based semantic scoring approach.

## Key Findings from the Repository

1. **Contribution distribution is uneven.**  
   A relatively small number of contributors account for a large portion of commits and pull requests, which suggests that the project depends heavily on a core group of maintainers.

2. **Contributor specialization is visible in the heatmap.**  
   The module-level heatmap shows that certain contributors repeatedly modify the same parts of the codebase, indicating informal ownership of specific components.

3. **Activity patterns vary significantly across contributors.**  
   Some contributors show consistent activity over time, while others appear as one-time contributors who submit a single pull request.

4. **Recent activity provides a better signal than historical totals.**  
   Contributors with high historical commit counts are not always the most active recently. Recency metrics help identify currently active maintainers.


## Limitations of the Autorater

Although the autorater attempts to evaluate contribution quality, it has several limitations:

- **LLM interpretation may be imperfect.**  
  The model evaluates PR titles, descriptions, and file lists, but it does not fully understand the code semantics or the broader architecture of the project.

- **Limited context.**  
  The system evaluates pull requests independently and does not account for long-term project planning, roadmap discussions, or design decisions.

- **Sampling constraints.**  
  Only a subset of commits and pull requests are analyzed to keep API usage manageable, which may omit some contributor activity.

- **Code review depth is difficult to measure automatically.**  
  Some high-impact work may occur through discussions or design proposals that are not easily captured by automated metrics.

## Future Improvements

If given more development time, several improvements could make the system more robust:

1. **Longitudinal contributor analysis**  
   Track contributor activity trends over time to identify rising contributors and declining participation.

2. **Contributor clustering**  
   Group contributors based on the parts of the codebase they modify to identify natural teams within the project.

3. **Improved code impact analysis**  
   Incorporate deeper analysis of code diffs and dependency graphs to better estimate the real impact of a change.

4. **Integration with additional repository signals**  
   Signals such as CI results, issue discussions, and design proposals could provide a richer understanding of contributor impact.

## Visualizations


### Dashboard overview + commit graph
The dashboard provides an overview of repository health by displaying key statistics such as stars, forks, open issues, number of contributors, and commits fetched. These metrics help quickly understand the scale and activity level of the repository.

The commit activity visualization shows how development activity evolves over time. Peaks in the graph represent periods of higher development activity, while lower areas indicate slower development periods.

<img width="1507" height="799" alt="1" src="https://github.com/user-attachments/assets/ad1dee4a-2dc3-4382-9347-d55def41d5e4" />


### Contributor Leaderboard
The contributor leaderboard aggregates multiple signals such as commits, pull requests, issues, and recent activity. This table helps identify the most active contributors and provides insight into how work is distributed across the contributor community.

<img width="1206" height="571" alt="2" src="https://github.com/user-attachments/assets/c7b5ddfb-ad0a-4fdb-b453-34237f8839d2" />


### Code Ownership Heatmap

The code ownership heatmap shows the relationship between contributors and the modules they modify. Darker cells represent a higher number of file modifications. This helps identify areas of the codebase where certain contributors have stronger ownership.

<img width="1236" height="545" alt="3" src="https://github.com/user-attachments/assets/591198fb-fc12-4c5b-a9d5-cdb6ad2c157e" />

### LLM Contributor Evaluation

The LLM-based autorater evaluates contributors using information extracted from their pull requests. The system generates structured scores across several dimensions including code quality, problem significance, review engagement, and contribution consistency.

<img width="1448" height="433" alt="4" src="https://github.com/user-attachments/assets/d30146a9-20ce-4bdc-ad40-25fb40e6ca89" />


### Bus Factor Estimation
The bus factor estimate measures how dependent the project is on a small number of contributors. In this case, the top contributor accounts for approximately 30% of commits, resulting in an estimated bus factor of 2, which indicates moderate reliance on key contributors.

<img width="509" height="252" alt="5" src="https://github.com/user-attachments/assets/27c00867-1ed2-40f4-b4e4-7ef5f93e6fe1" />

## Key Findings from the Analysis
- The repository shows extremely high community adoption

The repository statistics indicate that OpenClaw has 304,441 stars and 57,534 forks, demonstrating extremely high community interest and adoption. This suggests that the project has a large developer ecosystem and active external engagement.

- Contribution activity is concentrated among a few contributors

The contributor leaderboard shows that some contributors have significantly higher activity levels than others. For example, the contributor “steipete” has the highest number of commits in the sampled dataset (60 commits) and a very high total contribution count (11,859). This suggests that a few key maintainers play an important role in sustaining development.

- Contributors often specialize in specific parts of the codebase

The code ownership heatmap shows that contributors repeatedly modify certain modules, particularly directories such as src, docs, and extensions. This indicates that contributors tend to specialize in specific components of the project, forming informal ownership over parts of the codebase.

- Commit activity shows bursts of development

The commit activity graph shows that development occurs in bursts rather than at a constant rate. A significant spike in commits appears around one of the recent days in the analysis period, indicating periods of intense development activity followed by quieter periods.

- Bus factor analysis suggests moderate contributor dependency

The estimated bus factor is 2, meaning that the project depends on a small number of core contributors for maintaining development activity. While the repository has many contributors overall, the development workload appears to be concentrated among a few key maintainers.

- LLM-based autorater highlights differences in contributor impact


The LLM based autorater evaluation shows that contributors may differ in impact even if they have multiple commits. For example, the contributor steipete receives a total score of 60, indicating strong code quality and consistency but relatively low review engagement. This suggests that the contributor mainly focuses on code contributions rather than reviewing other pull requests.

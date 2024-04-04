# Run:ai cluster migration script

Goal:
The script helps automate the task of moving the following objects from one cluster to another:
- Projects
- Departments
- Node Pools
- Access Rules

How to use:
1. copy/clone the file from the repository
2. Install the requests library ```pip install requests```
3. Under ```if __name__ == "__main__"``` edit the BASE_URL, CLEINT_ID, CLIENT_SECRET, REALM
4. Under the two ```Cluster()``` objects, edit the ```cluster_id``` to match the cluster id of the current production/old cluster, and the cluster id of the new cluster<br />
***Make sure to put the correct cluster ID of the production cluster first, and the new cluster second***
5. Run the script:
   ```python3 main.py```

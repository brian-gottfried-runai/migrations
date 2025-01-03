import sys
import os
import json
import requests
from dataclasses import dataclass

@dataclass
class Cluster:
    base_url: str
    client_id: str
    client_secret: str
    cluster_id: str

    def generate_api_token(self):
        payload = {"grantType": "app_token", "AppId": self.client_id, "AppSecret": self.client_secret}
        headers = {'content-type': "application/json"}
        url = f"{self.base_url}/api/v1/token"
        try:
            response = requests.post(url=url, json=payload, headers=headers)
            response.raise_for_status()
            response_json = response.json()
            if "accessToken" not in response_json:
                raise SystemExit(f"failed to get access token from response. response body={response_json}")

            return response_json["accessToken"]

        except requests.exceptions.HTTPError as err:
            print(f"failed to get api token. err={err} \n message={err.response.text}" )
            raise SystemExit(err)
        except requests.exceptions.JSONDecodeError as err:
            print(f"failed to decode json response. err={err}")
            raise SystemExit(err)


def build_node_pool_resources_from_json(json_data, node_pools_map):
    return             {
                "nodePool": {
                    "name": json_data["nodePool"]["name"],
                    "id": f"{node_pools_map[json_data["nodePool"]["name"]]}",
                },
                "gpu": {
                    "deserved": json_data["gpu"]["deserved"],
                    "limit": json_data["gpu"]["maxAllowed"],
                    "overQuotaWeight": json_data["gpu"]["overQuotaWeight"]
                },
            }

def build_node_pool_schema_from_json(json_data):
    return {
        "id": json_data["id"],
        "name": json_data["name"],
        "overProvisioningRatio": 1,
        "labelKey": json_data["labelKey"],
        "labelValue": json_data["labelValue"],
        "placementStrategy": {
            "cpu": json_data["placementStrategy"]["cpu"],
            "gpu": json_data["placementStrategy"]["gpu"]
            }
    }

def build_department_schema_from_json(json_data, node_pools_map):
    return {
        "name": json_data["name"],
        "nodePoolsResources":  [build_node_pool_resources_from_json(node_pool_resource, node_pools_map=node_pools_map) for node_pool_resource in json_data["nodePoolsResources"]],
    }

def build_project_schema_from_json(json_data):
    return {
        "name": json_data["name"],
        "departmentId": int(json_data["departmentId"]),
        "clusterUuid": json_data["clusterUuid"],
        "defaultNodePools": json_data["defaultNodePools"] if json_data["defaultNodePools"] is not None else [],
        "permissions": {
        "users": json_data["permissions"]["users"] if json_data["permissions"]["users"] is not None else [],
        "groups": json_data["permissions"]["groups"] if json_data["permissions"]["groups"] is not None else [],
        "applications": []
        },
        "nodeAffinity": json_data["nodeAffinity"] if json_data["nodeAffinity"] is not None else [],
        "interactiveJobTimeLimitSecs": json_data["interactiveJobTimeLimitSecs"] if json_data["interactiveJobTimeLimitSecs"] is not None else [],
        "interactiveJobMaxIdleDurationSecs": json_data["interactiveJobMaxIdleDurationSecs"] if json_data["interactiveJobMaxIdleDurationSecs"] is not None else [],
        "interactivePreemptibleJobMaxIdleDurationSecs": json_data["interactivePreemptibleJobMaxIdleDurationSecs"] if json_data["interactivePreemptibleJobMaxIdleDurationSecs"] is not None else [],
        "trainingJobTimeLimitSecs": json_data["trainingJobTimeLimitSecs"] if json_data["trainingJobTimeLimitSecs"] is not None else [],
        "trainingJobMaxIdleDurationSecs": json_data["trainingJobMaxIdleDurationSecs"] if json_data["trainingJobMaxIdleDurationSecs"] is not None else [],
        "nodePoolsResources": json_data["nodePoolsResources"]
        
    }

def restore_json_from_file(file_name):
    try:
        with open(file_name, "r", encoding='utf-8') as file:
            return json.load(file)
    except json.decoder.JSONDecodeError as err:
        print(f"error retrieving json from {file_name}: {err}")
        return None
    
#Used to retrieve environment, compute, and datasource asset ids for creating templates
def get_id_by_name(apiEndpoint,resourceName):
        response = requests.get(f"{cluster.base_url}/{apiEndpoint}", headers=headers, params=f"name={resourceName}")
        response.raise_for_status()
        return response.json()["entries"][0]["meta"]["id"]


if __name__ == "__main__":

    cluster = Cluster(
        base_url="https://cs-bgottfri-jhu-2-18.runailabs-cs.com",
        client_id="migration",
        client_secret="buvzBu7XF0mEzvHfGqdMzo0SrPlpTyu2",
        cluster_id="6125a62b-44fc-4f11-846c-ec3754d74a98"
    )

    old_cluster_cluster_id="302809a4-d8e9-45be-b9ef-6eef5d793900"

    token = cluster.generate_api_token()
    headers = {"authorization": f"Bearer {token}", 'content-type': "application/json"}
    directory_name="2.16_cluster_json"
    
    ##### NodePools #####
    node_pools_map={}

    node_pools = restore_json_from_file(f"{directory_name}/node_pool.json")
    # print(node_pools)
    for node_pool in node_pools:
        node_pool = build_node_pool_schema_from_json(node_pool)
        node_pools_map[node_pool["name"]] = node_pool["id"]

    ##### Departments #####
    old_departments_map={}

    departments = restore_json_from_file(f"{directory_name}/department.json")
    for department in departments:
        old_departments_map[department["name"]] = department["id"]
        build_department_schema_from_json(json_data=department, node_pools_map=node_pools_map)

    ##### Projects #####
    old_projects_map = {}
    projects = restore_json_from_file(f"{directory_name}/project.json")
    for project in projects:
        old_projects_map[project["id"]] = project["name"]
    
    
    ######################### Node Pools #########################
    print('\n')
    print("######################### Node Pools #########################")
    print('\n')


    node_pools_list = [build_node_pool_schema_from_json(node_pool) for node_pool in node_pools]

    for node_pool in node_pools_list:
        if node_pool["name"] == "default":
            continue
        print(f"Creating node pool: {node_pool["name"]}...")
        response = requests.post(f"{cluster.base_url}/v1/k8s/clusters/{cluster.cluster_id}/node-pools", headers=headers, json=node_pool)
        
        if response.status_code == 409 and "already exists" in response.text:
            print(f"Skipping existing node pool {department["name"]}")
            continue
        elif response.status_code > 202:
            raise SystemExit(response.text)
        else:
            print(response.status_code)
        

    ######################### Departments #########################
    print('\n\n')
    print("######################### Departments #########################")
    print('\n')

    node_pools_map = {}
    response = requests.get(f"{cluster.base_url}/v1/k8s/clusters/{cluster.cluster_id}/node-pools", headers=headers)
    response.raise_for_status()
    node_pools = response.json()

    for node_pool in node_pools:
        node_pools_map[node_pool["name"]]=node_pool["id"]
    
    for department in departments:
        if department["name"] == "default":
            print(f"Skipping default department...")
            continue
        print(f"Creating department: {department["name"]}...")
        for i, node_pool_resource in enumerate(department["nodePoolsResources"]):
            # Change node_pool ID from 2.16 to the correct id in 2.13
            node_pool_resource["nodePool"]["id"] = node_pools_map[node_pool_resource["nodePool"]["name"]]
            # department = build_department_schema_from_json(department, node_pools_map=node_pools_map)
            node_pool_resource = build_node_pool_resources_from_json(node_pool_resource, node_pools_map=node_pools_map)
            department["nodePoolsResources"][i] = node_pool_resource
        print(f"Old Department json: {department}")
        new_department_json={}
        new_department_json["name"]=department["name"]
        new_department_json["clusterId"]=cluster.cluster_id
        new_department_json["resources"]=department["nodePoolsResources"]
        print("--------")
        print(f"New Department json: {new_department_json}")
        response = requests.post(f"{cluster.base_url}/api/v1/org-unit/departments", headers=headers, json=new_department_json)
        if response.status_code == 409 and "already exists" in response.text:
            print(f"Skipping existing department {department["name"]}")
            continue
        elif response.status_code > 202:
            raise SystemExit(response.text)
        else:
            print(response.status_code)


    ######################### Projects #########################
    print('\n\n')
    print("######################### Projects #########################")
    print('\n')

    old_departments_map_id_to_new_id = {}
    new_departments_map = {}
    response = requests.get(f"{cluster.base_url}/v1/k8s/clusters/{cluster.cluster_id}/departments", headers=headers)
    response.raise_for_status()
    departments = response.json()
    
    for department in departments:
        old_departments_map_id_to_new_id[old_departments_map[department["name"]]] = department["id"]
        new_departments_map[department["name"]] = department["id"]

    for project in projects:
        print(f"Creating project: {project["name"]}...")
        project["departmentId"] = old_departments_map_id_to_new_id[project["departmentId"]]
        for i, node_pool_resource in enumerate(project["nodePoolsResources"]):
            project_node_pool_resource_name = project["nodePoolsResources"][i]["nodePool"]["name"]
            project["nodePoolsResources"][i]["nodePool"]["id"] = node_pools_map[project_node_pool_resource_name]
        response = requests.post(f"{cluster.base_url}/v1/k8s/clusters/{cluster.cluster_id}/projects", headers=headers, json=project)
        if response.status_code == 409 and "already exists" in response.text:
            print(f"Skipping existing project {project["name"]}")
            continue
        elif response.status_code > 202:
            raise SystemExit(response.text)
        else:
            print(response.text)


    ######################### Access Rules #########################
    print('\n\n')
    print("######################### Access Rules #########################")
    print('\n')

    access_rules_json=restore_json_from_file(f"{directory_name}/access_rule.json")
    access_rules = access_rules_json["accessRules"]
    
    # Prepare relevant maps
    new_projects_map = {}
    response = requests.get(f"{cluster.base_url}/v1/k8s/clusters/{cluster.cluster_id}/projects", headers=headers)
    response.raise_for_status()
    projects = response.json()
    for project in projects:
        new_projects_map[project["name"]] = project["id"]

    old_projects_id_to_new = {}
    for key, value in old_projects_map.items():
        old_projects_id_to_new[key] = new_projects_map[value]
    

    for access_rule in access_rules:
        # Skip any clusters that do not belong to 2.16 for now, or if clusterId empty
        # if "clusterId" not in access_rule:
        #     continue
        # if access_rule["clusterId"] != old_cluster_cluster_id:
        #     continue
        # Removing unused fields in post request
        for key in ["roleName","scopeName","createdAt","updatedAt","createdBy","id","tenantId","clusterId"]:
            try:
                del access_rule[key]
            except KeyError as err:
                continue
        
        if access_rule["scopeType"] == "project":
            access_rule["scopeId"] = str(old_projects_id_to_new[int(access_rule["scopeId"])])
        elif access_rule["scopeType"] == "department":
            access_rule["scopeId"] = str(old_departments_map_id_to_new_id[int(access_rule["scopeId"])])
        elif access_rule["scopeType"] == "cluster":
            access_rule["scopeId"] = cluster.cluster_id

        print(f"Creating access rule {access_rule}...")
        response = requests.post(f"{cluster.base_url}/api/v1/authorization/access-rules", headers=headers, json=access_rule)
        if response.status_code == 409 and "already exists" in response.text:
            print(f"Skipping existing access rule {access_rule}")
            continue
        elif response.status_code > 202 and response.status_code < 409:
            print(response.text)
            raise SystemExit(response.text)
        else:
            print(response.text)

    # ######################### Local Users #########################
    # print('\n\n')
    # print("######################### Local Users #########################")
    # print('\n')

    # local_users_json=restore_json_from_file(f"{directory_name}/users.json")
    # local_users = local_users_json

    # for user in local_users:
    #     print(f"Creating local user {user}...")
    #     body=access_rule
    #     for key in body.keys():
    #         if key!="username":
    #             del body[key]
    #     response = requests.post(f"{cluster.base_url}/api/v1/users", headers=headers, json=body)


    ######################### Environment,Compute,Datasource,Workload Template #########################
    for resourceType in ["environment","compute","datasource","workload-template"]:
        print('\n\n')
        print(f"######################### {resourceType}s #########################")
        print('\n')
        resourceType_json=restore_json_from_file(f"{directory_name}/{resourceType}.json")
        resources = resourceType_json["entries"]

        for entry in resources:
            # Removing unused fields in post request
            meta=entry["meta"]
            #Set apiEndpoint before removing "kind" from "meta" block - necessary for datasources
            apiEndpoint=f"api/v1/asset/{resourceType}"
            if resourceType=="datasource":
                datasourceKind=meta["kind"]
                apiEndpoint=f"{apiEndpoint}/{datasourceKind}"
            for key in ["createdAt","updatedAt","updatedBy","createdBy","id","tenantId","clusterId", "kind","projectName"]:
                try:
                    del meta[key]
                except KeyError as err:
                    continue
            if meta["scope"] == "project":
                meta["projectId"] = old_projects_id_to_new[int(meta["projectId"])]
            elif meta["scope"] == "department":
                meta["departmentId"] = str(old_departments_map_id_to_new_id[int(meta["departmentId"])])
            elif meta["scope"] == "cluster":
                meta["clusterId"] = cluster.cluster_id

            if resourceType=="compute":
                #clean up spec fields based on other fields
                spec=entry["spec"]
                if spec["gpuDevicesRequest"]!=1:
                    del spec["gpuRequestType"]

            if resourceType=="datasource":
                #move all entries under datasourceKind to directly under spec and then remove datasourceKind
                for field in entry["spec"][datasourceKind]:
                    entry["spec"][field]=entry["spec"][datasourceKind][field]
                del entry["spec"][datasourceKind]

            if resourceType=="workload-template":
                #Get ids of created assets to set in template json
                assets=entry["spec"]["assets"]
                try:
                    assets["environment"]=get_id_by_name(f"/api/v1/asset/environment",assets["environment"]["name"])
                except KeyError as err:
                    pass
                try:
                    assets["compute"]=get_id_by_name(f"/api/v1/asset/compute",assets["compute"]["name"])
                except KeyError as err:
                    pass
                try:
                    for datasource in assets["datasources"]:
                        datasource["id"]=get_id_by_name(f"/api/v1/asset/datasource/{datasource["kind"]}",datasource["name"])
                        #Remove datasource name field since it's not in template API spec
                        del datasource["name"]
                    #TO-DO: Remove this line once issue with workloadSupportedTypes field is resolved
                except KeyError as err:
                    pass
                try:
                    del entry["meta"]["workloadSupportedTypes"]
                except KeyError as err:
                    pass

            


            print(f"Creating {resourceType} {meta["name"]} using {apiEndpoint}: {entry}...\n")
            response = requests.post(f"{cluster.base_url}/{apiEndpoint}", headers=headers, json=entry)
            if response.status_code == 409 and "already exists" in response.text:
                print(f"Skipping existing {resourceType} {meta["name"]}\n")
                continue
            elif response.status_code > 202 and response.status_code < 409:
                print(response.text)
                raise SystemExit(response.text)
            else:
                print(response.text)
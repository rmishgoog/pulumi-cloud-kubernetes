"""A Google Cloud Python Pulumi program"""

import pulumi
import pulumi_gcp as gcp

"""
Read the configuration for the stack. This dictionary is local to the stack, you can refer the values in Pulum.<stack>.yaml!
Reading the provider configurations which exists at the provider package level.
"""
provider_stack_config = pulumi.Config("gcp")
region = provider_stack_config.require("region")
project_name = provider_stack_config.require("project")
#Read the configuration from stack's own namespace.
generic_stack_config = pulumi.Config("kubernetes")
#Define the network arguments and then create a Google Cloud VPC network.
network_name = generic_stack_config.require("network")
network_options = gcp.compute.NetworkArgs(name=network_name,auto_create_subnetworks=False, routing_mode=generic_stack_config.require("routingmode"), description="Pulumi & GKE proofing network")
vpc_network = gcp.compute.Network(network_name,network_options)
#Create a subnetwork in us-east4 region within the VPC network created above.
subnet_name = generic_stack_config.require("subnetwork")
subnet_cidr = generic_stack_config.require("subnetwork-cidr")
vpc_sub_network = gcp.compute.Subnetwork(resource_name=subnet_name,network=vpc_network.id,ip_cidr_range=subnet_cidr,name=subnet_name,private_ip_google_access=True,region=region)
#Create a Google Cloud IAM service account to be assigned to the compute engine nodes and assign it minimal IAM roles it needs.
service_account_name = generic_stack_config.require("service-account")
gke_node_service_account = gcp.serviceaccount.Account(resource_name=service_account_name, account_id=service_account_name, display_name=service_account_name, project=project_name)
gke_policy_logging = gcp.projects.IAMMember(resource_name="gke-policy-logging",role="roles/logging.logWriter",member=gke_node_service_account.email.apply(lambda email: f'serviceAccount:{email}')
                                            ,project=project_name)
gke_policy_metrics_writer = gcp.projects.IAMMember(resource_name="gke-policy-metric-writer",role="roles/monitoring.metricWriter",member=gke_node_service_account.email.apply(lambda email: f'serviceAccount:{email}'),
                                                   project=project_name)
gke_policy_monitoring = gcp.projects.IAMMember(resource_name="gke-policy-monitoring",role="roles/monitoring.viewer",member=gke_node_service_account.email.apply(lambda email: f'serviceAccount:{email}'),
                                               project=project_name)
gke_policy_autoscale_metric_writer = gcp.projects.IAMMember(resource_name="gke-policy-as-metric-writer",role="roles/autoscaling.metricsWriter",member=gke_node_service_account.email.apply(lambda email: f'serviceAccount:{email}'),
                                                            project=project_name)

#Create a Google Kubernetes Engine (GKE) cluster on this subnet.
cluster_name = generic_stack_config.require("cluster-name")
gke_proofing_cluster = gcp.container.Cluster(resource_name=cluster_name, name=cluster_name,
    location=region,
    remove_default_node_pool=True,
    identity_service_config=gcp.container.ClusterIdentityServiceConfigArgs(
        enabled=False,
    ),
    enable_shielded_nodes=True,
    network=vpc_network.name,
    subnetwork=vpc_sub_network.name,
    networking_mode=generic_stack_config.require("cluster-mode"),
    ip_allocation_policy=gcp.container.ClusterIpAllocationPolicyArgs(
        cluster_ipv4_cidr_block=generic_stack_config.require("pod-cidr"),
        services_ipv4_cidr_block=generic_stack_config.require("svc-cidr"),
    ),
    addons_config=gcp.container.ClusterAddonsConfigArgs(
        dns_cache_config=gcp.container.ClusterAddonsConfigDnsCacheConfigArgs(
            enabled=True,
        ),
        gce_persistent_disk_csi_driver_config=gcp.container.ClusterAddonsConfigGcePersistentDiskCsiDriverConfigArgs(
            enabled=True,
        ),
    ),
    network_policy=gcp.container.ClusterNetworkPolicyArgs(
        enabled=True,
    ),
    initial_node_count=1, 
    private_cluster_config=gcp.container.ClusterPrivateClusterConfigArgs(
        enable_private_nodes=True,
        master_ipv4_cidr_block=generic_stack_config.require("master-ipv4-cidr"),
    ))

#Create a nodepool and associate it with GKE cluster created above, for proofing stack use preemptible nodes.
nodepool_name = generic_stack_config.require("nodepool-name")
gke_primary_preempt_nodepool_1 = gcp.container.NodePool(resource_name=nodepool_name, name=nodepool_name,location=region, cluster=gke_proofing_cluster.name,
                                                        node_count=1, node_config=gcp.container.NodePoolNodeConfigArgs(preemptible=True,
                                                                                                                       machine_type=generic_stack_config.require("node-machine-type"),
                                                                                                                       service_account=gke_node_service_account.email,
                                                                                                                       disk_size_gb= 10,
                                                                                                                       oauth_scopes=["https://www.googleapis.com/auth/cloud-platform"],))

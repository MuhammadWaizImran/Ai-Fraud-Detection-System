variable "resource_group_name" {
  type        = string
  default     = "rg-fraud-detection"
  description = "The name of the Azure Resource Group"
}

variable "location" {
  type        = string
  default     = "eastus"
  description = "Azure Region for all resources"
}

variable "project_name" {
  type        = string
  default     = "FraudDetection"
  description = "Project tag name"
}

variable "environment" {
  type        = string
  default     = "dev"
  description = "Environment name"
}

variable "eventhub_partition_count" {
  type        = number
  default     = 4
  description = "Number of partitions for the Event Hub topic"
}

variable "eventhub_retention_days" {
  type        = number
  default     = 1
  description = "Message retention in days"
}

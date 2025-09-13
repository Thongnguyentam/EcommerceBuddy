Restart product catalog service to get the most recent product list

```
# Option 1: Restart the pod (what you've been doing)
kubectl delete pod -l app=productcatalogservice

# Option 2: Send SIGUSR1 signal to reload catalog without restart
kubectl exec deployment/productcatalogservice -- kill -USR1 1

# Option 3: Scale down and up
kubectl scale deployment productcatalogservice --replicas=0
kubectl scale deployment productcatalogservice --replicas=1
```


```
k delete pod/<pod_id>
```
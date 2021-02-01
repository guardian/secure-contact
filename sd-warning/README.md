# sd-warning

A simple hidden service that warns our users that the onion v2 address for securedrop is no longer available and tells them to check out theguardian.com/securedrop

## How to deploy

In order to deploy you need a bucket with the `hidden_service` hostname and private key and the content of `static` in at the root.

The bucket in the `editorial-systems-development` account is called `sd-warning`.

You then deploy the cloud formation, pointing it at a `secure-contact` AMI and provide the bucket name and a public VPC.

That should be it, the launch config should manage the rest...

# Security Policy

## Reporting a vulnerability

Please don't open a public issue for a security problem. Report it privately from the **Security** tab of this repository, with **Report a vulnerability**. The maintainer answers there.

## What counts as a security problem here

- A skill or script that prints, logs or commits a secret, such as an API key or a token
- Anything that reads `.env` files or a user's browser data
- A path where the skills write to a product's source code, which must stay read-only
- Anything that sends a user's code or data somewhere other than the model and the services the user configured

## Supported versions

The project is pre-1.0. Only the latest commit on `main` gets fixes.

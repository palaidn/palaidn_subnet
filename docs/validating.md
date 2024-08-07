# Guide for Validators

1. Obtain API key(s) from Alchemy and PayPangea. You will be prompted to add them when you run the code in the next step.

3. Run `source ./scripts/start_validator.sh` and follow prompts. 

3. Check if .env file was created in your root directory with the following:

```bash
ALCHEMY_API_KEY=<YOUR_API_KEY>
PAYPANGEA_API_KEY=<YOUR_API_KEY>
```

>[!NOTE]
> We recommend running with --logging.trace while we are in Beta. This is much more verbose, but it will help us to debug if you run into issues.
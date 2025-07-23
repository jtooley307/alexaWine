#README for Alexa Wine Skill - Modernized

A robust Alexa skill that allows users to search for wines and get detailed information about them. This skill has been completely modernized with security fixes, error handling, and best practices.

## 🚀 Key Improvements

### Security & Configuration
- ✅ **Environment Variables**: API keys and configuration moved to environment variables
- ✅ **HTTPS**: All external API calls use secure HTTPS connections
- ✅ **Input Validation**: Comprehensive validation and sanitization of user input
- ✅ **No Hardcoded Secrets**: API keys are properly externalized

### Architecture & Dependencies
- ✅ **Modern SDK**: Upgraded from deprecated alexa-sdk v1 to ask-sdk-core v2
- ✅ **Node.js 18.x**: Updated from outdated Node.js 4.3 runtime
- ✅ **Modular Design**: Code split into logical modules (config, utils, services)
- ✅ **Proper Error Handling**: Comprehensive error handling with user-friendly messages

### Robustness & Reliability
- ✅ **Session Management**: Uses session attributes instead of global variables
- ✅ **Timeout Handling**: HTTP requests have proper timeout and retry logic
- ✅ **Structured Logging**: Proper logging with different log levels
- ✅ **Graceful Degradation**: Skill handles API failures gracefully

Need to install
- .bash_profile for env variables
- AWS cli tools
- Python and PIP
- Serverless for deployments
- Visual Studio (open source)
- alexa-sdk
- need to setup AWS account, and alexa SDK account


#deployments

I use serverless.  So you need to install it.  Then update the serverless.yml file

serverless create --template aws-nodejs

 set up a AWS and Alex account and skill

 npm install alexa-sdk
 

 serverless deploy

 Revison Notes

 1.0.1  improved logging
 1.0    Jan-06-2017 first certified Alexa release

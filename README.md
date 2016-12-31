README for Alexa Skills for finding Wine

This uses the alexa SDK, and the wine.com api.  You can find the rating, location, and description of wines.

The wine.com api is not very exact, so I try do rank results by popularity.  Needs more work.

#Installation

To use these programs you must download and install 'node' from http://nodejs.org

	npm install -g teslams
	
or if you are not logged in as the root (administrator) use:
	
	sudo npm install -g teslams

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

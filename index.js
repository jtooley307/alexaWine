'use strict';
var Alexa = require('alexa-sdk');
var http = require('http');
var utils = require('util');
var alexaDateUtil = require('./alexaDateUtil');

var states = {
    SEARCHMODE: '_SEARCHMODE',
    WINE_DETAILS: '_WINE_DETAILS',
};

// -- list of wines found -- 
var wineCount = 0;
var wineList = Array(); // name, price, rating, location, description
var currentWineIndex = 0;

// local variable holding reference to the Alexa SDK object
var alexa;

//OPTIONAL: replace with "amzn1.ask.skill.[your-unique-value-here]";
var APP_ID = "amzn1.ask.skill.db86c0db-cfb9-426f-99c5-dfc8406bd56f";

// Skills name
var skillName = "Sarah, the Wine Sommelier";

// Message when the skill is first called
var welcomeMessage = "You can ask Sarah for wine information.  Say, Find a wine by it's winery and name ";

// Message for help intent
var HelpMessage = "Here are some things you can say: Find a wine by giving its name. Tell me it's rating, price, location, or description.  What would you like to do?";

// Used to tell user skill is closing
var shutdownMessage = "Ok see you again soon.";
var goodbyeMessage = "Happy to help, good bye";

var searchHelpMessage = "Search Wine Help Message";

// used for title on companion app
var cardTitle = "Sarah, the Wine Sommelier";

// output for Alexa
var output = "";

var welcomeRepromt = 'You can ask me about a wine, then get details about the wine.  What are you interested in?';



function pr (str) {
    console.log(str);
}

// --------- Adding session handlers ----------------

var newSessionHandlers = {

    'LaunchRequest': function () {
        this.handler.state = states.SEARCHMODE;

        output = welcomeMessage;

        this.emit(':ask', output, welcomeRepromt);
    },
   
    'wineLocationIntent': function () {
        this.handler.state = states.SEARCHMODE;
        this.emitWithState('wineLocationIntent');
    },

    'wineSearchIntent': function(){
        this.handler.state = states.SEARCHMODE;
        this.emitWithState('wineSearchIntent');
    },
    'Unhandled': function () {
        output = HelpMessage;
        this.emit(':ask', output, welcomeRepromt);
    },
    'AMAZON.StopIntent': function () {
        this.emit(':tell', goodbyeMessage);
    },
    'SessionEndedRequest': function () {
        // Use this function to clear up and save any data needed between sessions
        this.emit('AMAZON.StopIntent');
    }
};


var startSearchHandlers = Alexa.CreateStateHandler(states.SEARCHMODE, {

    'AMAZON.HelpIntent': function () {
        output = HelpMessage;
        this.emit(':ask', output, HelpMessage);
    },

    'AMAZON.StartOverIntent': function () {
        // move to the next wine
        currentWineIndex = 0;
        output = "The first wine is " + wineList[currentWineIndex].name;
                
        this.emit(':ask', output, output);
    },


    'AMAZON.NextIntent': function () {
        // move to the next wine
        if (currentWineIndex < wineCount) {
            currentWineIndex++;
            output = "The next wine is, " + wineList[currentWineIndex].name;
        } else {
            output = "Sorry, we are at the end of the list.  You can go to the beginning by saying start over";
        }
        
        this.emit(':ask', output, output);
    },

    'AMAZON.PreviousIntent': function () {
         // move to the prev wine
        if (currentWineIndex > 0) {
            currentWineIndex--;
            output = "The previous wine is, " + wineList[currentWineIndex].name;
        } else {
            output = "Sorry, we are at the end of the list.  You can go to the beginning by saying start over";
        }
        this.emit(':ask', output, output);
    },

   'AMAZON.CancelIntent': function () {
        this.emit(':tell', goodbyeMessage);
    },

    'AMAZON.StopIntent': function () {
        this.emit(':tell', goodbyeMessage);
    },
  
    'AMAZON.RepeatIntent': function () {
        this.emit(':ask', output, HelpMessage);
    },

    'SessionEndedRequest': function () {
        // Use this function to clear up and save any data needed between sessions
        this.emit('AMAZON.StopIntent');
    },

    'Unhandled': function () {
        output = HelpMessage;
        this.emit(':ask', output, welcomeRepromt);
    },

    // -- custom intents --

    'getWineDetailsIntent': function() {
        output = "What details would you like? Price, Rating, Location, or Desription?";
        var cardTitle = "Wine Details";
        var intent = this.event.request.intent;
        var action = getActionFromIntent(intent);
        this.handler.state = states.WINE_DETAILS;  // put them into state to ask for details like rating, location, price, description
        if (!action.error) {
            // do wineActionDetailIntent'
            this.emitWithState('wineActionDetailIntent');
        } else {
            this.handler.state = states.WINE_DETAILS;  // put them into state to ask for details like rating, location, price, description
            alexa.emit(':askWithCard', output, output, cardTitle, output);
        }
    },


    'wineSearchIntent': function() {
        var output = 'Wine Search Intent';
        var intent = this.event.request.intent;
        var wineName = getWineFromIntent(intent, true);
        var wineDate = getDateFromIntent(intent);
        
        var searchExpression = wineName;
        var cardTitle = "Wine Search: " + wineName; 

        // reset index
        currentWineIndex = 0;
        wineCount = 0;
      
        getJsonFromWineShop(searchExpression, function(data){
            wineCount = data.Products.List.length;
            pr('wine count ' + wineCount);
            for (var i = 0; i < wineCount; i++) {
                 
                var wRating = data.Products.List[i].Ratings.HighestScore;
                var wPrice = data.Products.List[i].PriceRetail;
                var wDescription = data.Products.List[i].Varietal + " from " + data.Products.List[i].Vineyard;
                var wLocation = "";

                if (data.Products.List[i].Appellation != null) {
                    wLocation += data.Products.List[i].Appellation.Name;
                }
                if (data.Products.List[i].Appellation.Region != null) {
                    wLocation += " in " + data.Products.List[i].Appellation.Region.Name;
                }
                
                var wName = data.Products.List[i].Name;

                wineList[i] = {"name": wName, "rating": wRating, 'price': wPrice, 'location': wLocation, 'description': wDescription};

            }
            if (wineCount == 0  || data.Status.ReturnCode != 0) {
                output = 'That wine does not exist.';
              
            } else if (wineCount > 1) {
                output = "I found " + wineCount + " wines that match. You can go through the list by saying next or previous.  ";
                output = output + "The best match is, " + wineList[currentWineIndex].name;;
            
            } else if (wineCount == 1) {
                // found a match
                var text = wineList[currentWineIndex].name;  // name of wine returned
                output = text + ' has a rating of, ' + wineList[currentWineIndex].rating;       
            
            } else {
                output = 'That wine does not exist.';
            } 
             
            alexa.emit(':askWithCard', output, cardTitle, output);
        });
    },

    'testIntent': function () {
        output = searchHelpMessage;
        alexa.emit(':ask', 'testIntent', output);
    }

});

var wineDetailsHandlers = Alexa.CreateStateHandler(states.WINE_DETAILS, {
    
    'AMAZON.HelpIntent': function () {
        output = HelpMessage;
        this.emit(':ask', output, HelpMessage);
    },
    
    'AMAZON.CancelIntent': function () {
        this.handler.state = states.SEARCHMODE;
        alexa.emit(':ask', "Going back to the wine list.  Skip to a wine, or say stop", HelpMessage);
    },

    'AMAZON.RepeatIntent': function () {
        alexa.emit(':ask', output, HelpMessage);
    },

    'SessionEndedRequest': function () {
        // Use this function to clear up and save any data needed between sessions
        this.emit('AMAZON.StopIntent');
    },

    'Unhandled': function () {
        output = HelpMessage;
        alexa.emit(':ask', output, welcomeRepromt);
    },

    // -- custom intents -- 

    'wineActionDetailIntent': function () {
        var output = " ";
        var rePrompt = "If you are done then say back, cancel or done";
       
        this.handler.state = states.WINE_DETAILS;
        var intent = this.event.request.intent;
        var action = getActionFromIntent(intent);
        var cardTitle = "Wine Details: " + action;
        
        if (wineCount > 0) {
             var text = wineList[currentWineIndex].name;  // name of wine returned
             output = "The " + text + ' has the following details ';
            // actions can be location, price, rating, description
            if (action.indexOf('description') > -1 && wineList[currentWineIndex].Description.indexOf('undefined') == -1 ) {
            
                output += " is " + wineList[currentWineIndex].Description;
            }
            if (action.indexOf('location') > -1) {
                output += ', location is ' + wineList[currentWineIndex].location;
            }
            if (action.indexOf('rating') > -1 && wineList[currentWineIndex].rating > 0) {
                
                output += ', highest rating is ' + wineList[currentWineIndex].rating;
            } 
            if (action.indexOf('price') > -1 && wineList[currentWineIndex].price > 0) {
               
                output += ', price is $' + wineList[currentWineIndex].price;
            }
        }   
        alexa.emit(':askWithCard', output, rePrompt, cardTitle, output);
    }
});

exports.handler = function (event, context, callback) {
    alexa = Alexa.handler(event, context);
    alexa.AppId = APP_ID;
    alexa.registerHandlers(newSessionHandlers, startSearchHandlers, wineDetailsHandlers);
    alexa.execute();
};


// --------- Helpers ---------------

var API_KEY = "70b1bd8e9178f2b0abaf033e2a6c4067";
// http://services.wine.com/api/version/service.svc/format/resource?apikey=key&parameters
// http://services.wine.com/api/beta/service.svc/JSON/catalog?search=robert+mondavi+reserve+cabernet+Sauvigon+2013&size=3&sort=popularity&apikey=70b1bd8e9178f2b0abaf033e2a6c4067
// http://www.wine-searcher.com/Xkey=robert+mondavi&Xformat=J
var catalogPortal = 'https://services.wine.com/api/beta2/service.svc/JSON/catalog';

// alexa skill helper functions

var url = function(wineId){
  return 'http://services.wine.com/api/beta2/service.svc/JSON/catalog?search='+ wineId + '&size=5&sort=popularity&apikey=' + API_KEY;
};

var getJsonFromWineShop = function(descr, callback){
  http.get(url(descr), function(res){
    var body = '';

    res.on('data', function(data){
      body += data;
    });

    res.on('end', function(){
      var result = JSON.parse(body);
      callback(result);
    });

  }).on('error', function(e){
    console.log('Error: ' + e);
  });
};

function getWineFromIntent(intent, assignDefault) {

    var wineSlot = intent.slots.Wine;
    // slots can be missing, or slots can be provided but with empty value.
    // must test for both.
    if (!wineSlot || !wineSlot.value) {
        if (!assignDefault) {
            return {
                error: true
            }
        } else {
            // For sample skill, default to a favorite
            return {
                wine: 'Goldeneye Pinot Nior Confluence 2014'
            }
        }
    } else {
        return wineSlot.value;
    }
}

function getActionFromIntent(intent) {

    var actionSlot = intent.slots.Action;
    // slots can be missing, or slots can be provided but with empty value.
    // must test for both.
    if (!actionSlot || !actionSlot.value) {
        return {error: true}
            
    } 
    else {
        return actionSlot.value;
    }
}

/**
 * Gets the date from the intent, defaulting to today if none provided,
 * or returns an error
 */
function getDateFromIntent(intent) {

    var dateSlot = intent.slots.Date;
    // slots can be missing, or slots can be provided but with empty value.
    // must test for both.
    if (!dateSlot || !dateSlot.value) {
        // default to today
        var now = new Date();
        var requestDay = now.getFullYear();
        return {
            displayDate: "Today",
            requestDateParam: requestDay
        }
    } else {

        var date = new Date(dateSlot.value);

        // format the request date like YYYY
           var requestDay = date.getFullYear();

        return {
            displayDate: alexaDateUtil.getFormattedDate(date),
            requestDateParam: requestDay
        }
    }
}



const WineService = require('./wineService');

async function testWineDatabase() {
    console.log('🍷 Testing Local Wine Database...\n');
    
    const wineService = new WineService();
    
    try {
        // Test 1: Basic wine search
        console.log('Test 1: Searching for Cabernet Sauvignon...');
        const results = await wineService.searchWines('Cabernet Sauvignon');
        
        if (results && results.length > 0) {
            console.log(`✅ SUCCESS: Found ${results.length} wines`);
            console.log(`   First result: ${results[0].Name}`);
            console.log(`   Price: $${results[0].Price}`);
            console.log(`   Rating: ${results[0].Rating}/100`);
            console.log(`   Region: ${results[0].Region}`);
        } else {
            console.log('❌ FAILED: No results returned');
        }
        
        console.log('\n' + '='.repeat(50) + '\n');
        
        // Test 2: Search for specific wine type
        console.log('Test 2: Searching for Pinot Noir...');
        const pinotResults = await wineService.searchWines('Pinot Noir');
        
        if (pinotResults && pinotResults.length > 0) {
            console.log(`✅ SUCCESS: Found ${pinotResults.length} Pinot Noir wines`);
            console.log(`   Example: ${pinotResults[0].Name}`);
            console.log(`   Region: ${pinotResults[0].Region}`);
            console.log(`   Winery: ${pinotResults[0].Winery}`);
        } else {
            console.log('❌ FAILED: No Pinot Noir results');
        }
        
        console.log('\n' + '='.repeat(50) + '\n');
        
        // Test 3: Wine pairing functionality
        console.log('Test 3: Testing wine pairing for steak...');
        const pairingResults = await wineService.getWinePairings('steak');
        
        if (pairingResults && pairingResults.length > 0) {
            console.log(`✅ SUCCESS: Found ${pairingResults.length} wines for steak`);
            console.log(`   Recommendation: ${pairingResults[0].Name}`);
            console.log(`   Type: ${pairingResults[0].Type}`);
            console.log(`   Rating: ${pairingResults[0].Rating}/100`);
        } else {
            console.log('❌ FAILED: No pairing results');
        }
        
        console.log('\n' + '='.repeat(50) + '\n');
        
        // Test 4: Occasion-based recommendations
        console.log('Test 4: Testing wines for celebration...');
        const occasionResults = await wineService.getOccasionWines('celebration');
        
        if (occasionResults && occasionResults.length > 0) {
            console.log(`✅ SUCCESS: Found ${occasionResults.length} celebration wines`);
            console.log(`   Recommendation: ${occasionResults[0].Name}`);
            console.log(`   Price: $${occasionResults[0].Price}`);
        } else {
            console.log('❌ FAILED: No occasion results');
        }
        
        console.log('\n' + '='.repeat(50) + '\n');
        
        // Test 5: Random wine recommendation
        console.log('Test 5: Getting random wine recommendation...');
        const randomWine = await wineService.getRandomWine({ maxPrice: 50 });
        
        if (randomWine) {
            console.log(`✅ SUCCESS: Random wine selected`);
            console.log(`   Wine: ${randomWine.Name}`);
            console.log(`   Price: $${randomWine.Price}`);
            console.log(`   Type: ${randomWine.Type}`);
        } else {
            console.log('❌ FAILED: No random wine returned');
        }
        
    } catch (error) {
        console.log('❌ WINE DATABASE TEST FAILED:');
        console.log(`   Error: ${error.message}`);
        console.log(`   Stack: ${error.stack}`);
    }
}

// Run the test
testWineDatabase().then(() => {
    console.log('\n🏁 Wine Database Test Complete!');
}).catch(error => {
    console.error('💥 Test script failed:', error);
});

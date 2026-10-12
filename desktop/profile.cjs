'use strict';
const fs=require('node:fs'),path=require('node:path');
// Preserve profiles in place: cookies, protected credentials and managed backend paths.
function legacyProfile(appData){
 const candidates=['tren-desktop','TREN'].map(name=>path.join(appData,name));
 return candidates.find(dir=>fs.existsSync(path.join(dir,'installation.json')))||candidates[0];
}
module.exports={legacyProfile};

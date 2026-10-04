/* IMAGE CONTROL – paste your own verified photo URLs here (Unsplash / Pexels / Wikimedia Commons / PIB / your own files in /static/img).
   Slot key = the keyword string used in app.js. Any slot listed here overrides the automatic Flickr keyword photos. Example:
   window.KU_IMAGES={"solar,farm,india":["/static/img/solar1.jpg","https://images.pexels.com/photos/XXXX/pexels-photo-XXXX.jpeg"]}; */
window.KU_IMAGES={};
const PHOTO_TAGS={ // keyword → better-targeted flickr tags
 "solar,farm,india":"solar,farm","indian,farmer,wheat,field":"farmer,wheat,field","indian,farmer,smile":"farmer,india","irrigation,farm,water":"irrigation,farm","crop,leaf,plant":"crop,leaf"};
function IMG(k,n=1,w=640,h=420){const o=window.KU_IMAGES[k];if(o&&o.length)return o[n%o.length];return `https://loremflickr.com/${w}/${h}/${PHOTO_TAGS[k]||k}?lock=${n}`}

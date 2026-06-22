// ==============================
// CONFIG
// ==============================

const BASE_URL =
"";

let documentId =
null;




// ==============================
// FILE SIZE
// ==============================

function formatFileSize(bytes){

const kb =
bytes/1024;


return kb>1024

?

(kb/1024)
.toFixed(2)

+

" MB"

:

kb.toFixed(2)

+

" KB";

}




// ==============================
// GREETING
// ==============================

function setGreeting(){

const h =
new Date()
.getHours();


const g =
document.getElementById(
"greetingMsg"
);


if(h<12){

g.innerText=
"🌞 Good Morning!";

}

else if(h<18){

g.innerText=
"☀️ Good Afternoon!";

}

else{

g.innerText=
"🌙 Good Evening!";

}

}




// ==============================
// TYPING EFFECT
// ==============================

async function typeText(
element,
text,
speed = 15
){

element.innerHTML = "";

for(
let i=0;
i<text.length;
i++
){

element.innerHTML +=
text.charAt(i);


await new Promise(

resolve =>
setTimeout(
resolve,
speed
)

);

}

}




// ==============================
// SAVE RECENTS
// ==============================

function saveToRecents(
name,
size,
id
){

let recents =

JSON.parse(

localStorage.getItem(
"recents"
)

)

||

[];



recents.unshift({

name,
size,
id

});



recents =
recents.slice(
0,
5
);



localStorage.setItem(

"recents",

JSON.stringify(
recents
)

);



renderRecents();

}





// ==============================
// RENDER RECENTS
// ==============================

function renderRecents(){

const list =

document.getElementById(
"recentsList"
);



const recents =

JSON.parse(

localStorage.getItem(
"recents"
)

)

||

[];



list.innerHTML = "";



if(
!recents.length
){

list.innerHTML =

"<p>No recent files</p>";

return;

}



recents.forEach(

file=>{


const div =

document.createElement(
"div"
);



div.innerHTML =

`

📄 ${file.name}

<br>

<small>

${file.size}

</small>

`;




div.onclick = ()=>{


document

.getElementById(
"fileDetails"
)

.innerText =

`${file.name}

(${file.size})`;



documentId =

Number(
file.id
);



document

.getElementById(
"recentsList"
)

.classList

.remove(
"show"
);


};



list.appendChild(
div
);

}

);

}





// ==============================
// RECENTS TOGGLE
// ==============================

document

.getElementById(
"recentsBtn"
)

.addEventListener(

"click",

()=>{

document

.getElementById(
"recentsList"
)

.classList

.toggle(
"show"
);

}

);






// ==============================
// SETTINGS PANEL
// ==============================

document

.getElementById(
"settingsBtn"
)

.addEventListener(

"click",

()=>{


document

.getElementById(
"settingsPanel"
)

.classList

.toggle(
"show"
);


}

);






// ==============================
// LIGHT MODE
// ==============================

document

.getElementById(
"lightModeBtn"
)

.addEventListener(

"click",

()=>{


document.body

.classList

.remove(
"dark-mode"
);



localStorage.setItem(

"theme",

"light"

);


}

);






// ==============================
// DARK MODE
// ==============================

document

.getElementById(
"darkModeBtn"
)

.addEventListener(

"click",

()=>{


document.body

.classList

.add(
"dark-mode"
);



localStorage.setItem(

"theme",

"dark"

);


}

);



// ==============================
// ADD FILE BUTTON
// ==============================

document

.getElementById(
"addFileBtn"
)

.addEventListener(

"click",

()=>{

document

.getElementById(
"fileInput"
)

.click();

}

);






// ==============================
// FILE UPLOAD
// ==============================

document

.getElementById(
"fileInput"
)

.addEventListener(

"change",

async(
e
)=>{

const files =

e.target.files;
console.log("Files selected:", files.length);

if(
!files.length
)
return;

let fileNames = [];

const formData =

new FormData();

for(
let file of files
){

fileNames.push(
file.name
);

formData.append(
"files",
file
);

}

document

.getElementById(
"fileDetails"
)

.innerHTML =

fileNames.join(
"<br>"
);

try{

const res =

await fetch(

`${BASE_URL}/upload`,

{

method:
"POST",

body:
formData

}

);

const data =

await res.json();

if(
data.documents &&
data.documents.length > 0
){

documentId =

data.documents[0]
.document_id;

for(
let doc of data.documents
){

saveToRecents(

doc.filename,

"Uploaded",

doc.document_id

);

}

}

}

catch{

alert(
"Upload failed"
);

}

}
);






// ==============================
// ASK QUESTION
// ==============================

document

.getElementById(
"submitBtn"
)

.addEventListener(

"click",

async()=>{

const question =

document

.getElementById(
"questionInput"
)

.value

.trim();

const recents =

JSON.parse(
localStorage.getItem(
"recents"
)
) || [];

if(
recents.length === 0
){

alert(
"Upload at least one document first"
);

return;

}

if(
!question
){

return;

}



const responseBox =

document

.getElementById(
"responseBox"
);

responseBox.innerHTML +=

`

<div class="user-message">

👤 You

<br><br>

${question}

</div>

`;


// CREATE AI BUBBLE

const aiDiv =

document.createElement(
"div"
);

aiDiv.className =
"ai-message";

aiDiv.innerHTML =

`

🤖 AI

<br><br>

<span class="typing">

Thinking...

</span>

`;

responseBox.appendChild(
aiDiv
);

const typingSpan =

aiDiv.querySelector(
".typing"
);

responseBox.scrollTop =

responseBox.scrollHeight;

try{

const res =

await fetch(

`${BASE_URL}/ask`,

{

method:
"POST",

headers:{

"Content-Type":

"application/json"

},

body:

JSON.stringify({

question:

question

})

}

);

const data =

await res.json();

await typeText(

typingSpan,

data.answer,

15

);


// ==============================
// SHOW SOURCES
// ==============================

if (

data.sources &&

data.sources.length > 0

){

let sourceHtml =

"<br><br>📌 Sources:<br>";

data.sources.forEach(

src => {

sourceHtml +=

`${src.file}
(Chunk ${src.chunk})<br>`;

}

);

aiDiv.innerHTML +=

`

<div class="source-box">

${sourceHtml}

</div>

`;

}

document

.getElementById(
"questionInput"
)

.value = "";

responseBox.scrollTop =

responseBox.scrollHeight;

}

catch{

typingSpan.innerHTML =

"❌ Backend Error";

}

}

);



// ==============================
// PAGE LOAD
// ==============================

window.addEventListener(

"DOMContentLoaded",

()=>{


setGreeting();


renderRecents();




// restore theme

const savedTheme =

localStorage.getItem(
"theme"
);



if(
savedTheme==="dark"
){

document.body

.classList

.add(
"dark-mode"
);

}


}

);
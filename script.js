// Typing Effect
const text = ["AI Developer", "NLP Engineer", "Frontend Creator"];
let i = 0;
let j = 0;
let currentText = "";
let isDeleting = false;

function type() {
  currentText = text[i];

  if (!isDeleting) {
    document.getElementById("typing").textContent =
      currentText.substring(0, j++);
  } else {
    document.getElementById("typing").textContent =
      currentText.substring(0, j--);
  }

  if (j === currentText.length) isDeleting = true;
  if (j === 0) {
    isDeleting = false;
    i = (i + 1) % text.length;
  }

  setTimeout(type, isDeleting ? 50 : 100);
}

type();

// AOS init
AOS.init();

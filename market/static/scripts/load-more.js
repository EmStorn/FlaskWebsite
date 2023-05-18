// Set the number of rows to show initially and how many to add each time
var rowsToShow = 10;
var rowsToAdd = 5;

// Get a reference to the table and the button
var table = document.getElementById("admin-all-orders-table");
var loadMoreBtn = document.getElementById("load-more-btn");

// Keep track of the current number of rows shown
var currentRows = rowsToShow;

// Count the number of rows in the table
var numRows = table.querySelectorAll("tbody tr").length;

// Hide all rows beyond the initial set if there are at least 10 rows
if (numRows >= 10) {
  var rows = table.querySelectorAll("tbody tr");
  for (var i = rowsToShow; i < rows.length; i++) {
     rows[i].classList.add("extra-row");
  }
} else {
  // Hide the load more button if there are less than 10 rows
  loadMoreBtn.style.display = "none";
}

// Add an event listener to the button
loadMoreBtn.addEventListener("click", function() {
   // Show the next set of rows
   for (var i = currentRows; i < currentRows + rowsToAdd; i++) {
      if (i >= numRows) {
         // If there are no more rows to show, hide the button
         loadMoreBtn.style.display = "none";
         break;
      }
      rows[i].classList.remove("extra-row");
   }
   // Update the currentRows counter
   currentRows += rowsToAdd;
});

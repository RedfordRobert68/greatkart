
var amount = grand_total;

const paypalButtons = window.paypal.Buttons({
    style: {
        shape: "rect",
        layout: "vertical",
        color: "blue",
        label: "paypal",
    },
    message: {
        amount: 100,
    },

    createOrder: function(data, actions) {
        return actions.order.create({
            purchase_units: [{
                amount: {
                    value: amount
                }
            }]
        });
    },

    //Finalize the transaction
    onApprove: function(data, actions) {
        return actions.order.capture().then(function(details) {
            //Show a success message to the buyer
            console.log(details)
            alert('Transaction completed by ' + details.payer.name.given_name + '!');
        });
    }
   
});
paypalButtons.render("#paypal-button-container");


// Example function to show a result to the user. Your site's UI library can be used instead.
function resultMessage(message) {
    const container = document.querySelector("#result-message");
    container.innerHTML = message;
}
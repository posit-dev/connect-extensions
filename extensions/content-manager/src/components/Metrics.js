import m from "mithril";
import Metrics from "../models/Metrics";

const TimeseriesChart = {
  oncreate: function (vnode) {
      // Initialize the chart when the component is created
      const ctx = vnode.dom.getContext('2d');
      const labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'];
      const data = [10, 20, 15, 25, 30, 20];

      new Chart(ctx, {
          type: 'line',
          data: {
              labels: labels,
              datasets: [{
                  label: 'Views',
                  data: data,
                  borderColor: 'rgba(75, 192, 192, 1)',
                  backgroundColor: 'rgba(75, 192, 192, 0.2)',
                  tension: 0.4 // Smooth line
              }]
          },
          options: {
              responsive: true,
              maintainAspectRatio: false,
              scales: {
                  x: {
                      title: {
                          display: true,
                          text: 'Month'
                      }
                  },
                  y: {
                      title: {
                          display: true,
                          text: 'Value'
                      },
                      beginAtZero: true
                  }
              }
          }
      });
  },
  view: function () {
      return m('canvas', { style: 'width: 100%; height: 400px;' });
  }
};

export default {
  error: null,

  oninit: function (vnode) {
    try {
      Metrics.load(vnode.attrs.id);
    } catch (err) {
      this.error = "Failed to load data.";
      console.error(err);
    }
  },

  view: function (vnode) {
    if (this.error) {
      return m("div", { class: "error" }, this.error);
    }

    const metrics = Metrics.data;
    if (metrics === null) {
      return;
    }

    const start = Math.min(...metrics.map(metric => new Date(metric?.started)))
    const ended = Math.max(...metrics.map(metric => new Date(metric?.ended)))
    console.log(start, ended)

    return m(".pt-3.border-top", [
      m("h5", "Metrics"),
      m(TimeseriesChart),
    ]);
  },
};

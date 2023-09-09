import moment from 'moment';
const icalgen = require('ical-generator');

function generateIcsDownload(selectedCourses) {
	var cal = icalgen();
	cal.timezone('Europe/Berlin');
	console.log(selectedCourses)
	selectedCourses.forEach(cur => {
		cur.weekly
			.filter(w => !w.room.startsWith("Übung ") || selectuebungs[cur.id] === format_weekly(w))
			.forEach(element => {
				var startDate = moment.tz(element.firstdate, "YYYY-MM-DD", "Europe/Berlin");
				var endDate = startDate.clone();

				startDate.add(element.start[0], 'hours');
				startDate.add(element.start[1], 'minutes');

				endDate.add(element.end[0], 'hours');
				endDate.add(element.end[1], 'minutes');
				console.log(startDate.format());
				var eventObj = cal.createEvent({
					start: startDate,
					end: endDate,
					summary: cur.title_short,
					location: element.room
				});

				eventObj.timezone('Europe/Berlin');

				if (element.count > 1) {
					eventObj.repeating({
						freq: 'WEEKLY',
						count: element.count
					});
				}
			});
	});

	return cal.toURL();

}

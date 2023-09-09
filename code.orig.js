var ical = {
  vdt: d => d.getFullYear()
            + (d.getMonth()+1+"").padStart(2,'0')
            + (d.getDate()+"").padStart(2,'0')
            + "T"
            + (d.getHours()+"").padStart(2,'0')
            + (d.getMinutes()+"").padStart(2,'0')
            + (d.getSeconds()+"").padStart(2,'0'),

  ymd: d => d.getFullYear() + "-"
            + (d.getMonth()+1+"").padStart(2,'0') + "-"
            + (d.getDate()+"").padStart(2,'0'),

  vcalendar: function (dates) {
    var dates = dates.map(date => {
      var x = date.split("\t");
      return {start:new Date(x[0] + "T" + x[1]),
              end: new Date(x[0] + "T" + x[2]),
              title: x[4],
              location: x[3],};
    });

    return "BEGIN:VCALENDAR"
      + "\nPRODID:-//Beautiful Tucan via Javascript//DE"
      + "\nVERSION:2.0"
      + "\nBEGIN:VTIMEZONE"
      + "\nTZID:Europe/Berlin"
      + "\nBEGIN:DAYLIGHT"
      + "\nTZOFFSETFROM:+0100"
      + "\nTZOFFSETTO:+0200"
      + "\nTZNAME:CEST"
      + "\nDTSTART:19700329T020000"
      + "\nRRULE:FREQ=YEARLY;BYDAY=-1SU;BYMONTH=3"
      + "\nEND:DAYLIGHT"
      + "\nBEGIN:STANDARD"
      + "\nTZOFFSETFROM:+0200"
      + "\nTZOFFSETTO:+0100"
      + "\nTZNAME:CET"
      + "\nDTSTART:19701025T030000"
      + "\nRRULE:FREQ=YEARLY;BYDAY=-1SU;BYMONTH=10"
      + "\nEND:STANDARD"
      + "\nEND:VTIMEZONE"
      + dates.map(ical.vevent).join("")
      + "\nEND:VCALENDAR";
  },

  vevent: function (date) {
    return ""
      + "\nBEGIN:VEVENT"
      + "\nUID:" + Math.floor(Math.random()*0xffffffff).toString(16)
      + "\nDTSTAMP:" + ical.vdt(new Date())
      + "\nDTSTART;TZID=Europe/Berlin:" + ical.vdt(date.start)
      + "\nDTEND;TZID=Europe/Berlin:"   + ical.vdt(date.end)
      + "\nSUMMARY:" + date.title
      + "\nLOCATION:" + date.location
      + "\nEND:VEVENT";
  }
}

function generateIcsDownload(selectedCourses) {
    var calendardates = selectedCourses
      .flatMap(module => Object.values(module.content).map(x => [module, x]))
      .flatMap(x => [
        ...x[1].dates
          .map(y => y + "\t" + x[0].title_short),
        ...x[0].weekly
          .filter(w => w.room.startsWith("Übung ") && selectuebungs[x[0].id] === format_weekly(w)
                    || w.room.startsWith("Übungsstunde"))
          .flatMap(y =>
            [...Array(y.count).keys()].map(i =>
              ical.ymd(new Date(+new Date(y.firstdate) + 1000*60*60*24*7 * i))
            + "\t"+ format_timespan(y).replace(" - ", "\t") +"\t-\tÜbung " + x[0].title_short) )
      ]);

    return ical.vcalendar(calendardates)
}


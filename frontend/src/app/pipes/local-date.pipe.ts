import { Pipe, PipeTransform } from '@angular/core';
import { DatePipe } from '@angular/common';

@Pipe({
  name: 'localDate',
  standalone: false
})
export class LocalDatePipe implements PipeTransform {
  constructor(private datePipe: DatePipe) {}

  transform(value: any, format: string = 'short'): string | null {
    if (!value) return null;
    
    // If the value is a string and doesn't have timezone info, treat it as UTC
    if (typeof value === 'string' && !value.endsWith('Z') && !value.includes('+')) {
      // Add 'Z' to indicate UTC time
      value = value + 'Z';
    }
    
    // Convert to Date object and use Angular's date pipe which will convert to local timezone
    return this.datePipe.transform(value, format);
  }
}

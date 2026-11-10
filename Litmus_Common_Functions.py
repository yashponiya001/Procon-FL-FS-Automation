import os.path
import csv

class CsvFileWriter():
    def write_row_col(self, filename, row, col, text_to_write):
        f = open(filename, 'r')
        reader = csv.reader(f)
        mylist = list(reader)
        f.close()
        mylist[row][col] = text_to_write
        my_new_list = open(filename, 'w', newline='')
        csv_writer = csv.writer(my_new_list)
        csv_writer.writerows(mylist)
        my_new_list.close()



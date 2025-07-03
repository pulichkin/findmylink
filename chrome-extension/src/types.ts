export interface BookmarkTreeNode {
     id: string;
     title: string;
     url?: string;
     children?: BookmarkTreeNode[];
   }

   export interface Tab {
     id?: number;
     title?: string;
     url?: string;
   }

   export interface Subscription {
     user_id: number;
     end_date: string;
     active: boolean;
   }
